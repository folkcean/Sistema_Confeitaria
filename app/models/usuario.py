"""
models / usuario.py
Módulo de usuários e acessos de Sistema de Gestão de Confeitaria

Hierarquia do DER:
    Usuário (tabela USUÁRIO)
        ├── Cliente (tabela CLIENTE - PK/FK: USUÁRIOID_usuário)
        ├── Funcionário (tabela FUNCIONÁRIO - PK/FK: USUÁRIOID_usuário)
        └── Administrador (tabela ADMINISTRADOR - PK/FK: USUÁRIOID_usuário)
    Endereço (tabela ENDEREÇO - Cliente 1:N Endereço)
"""

# importa anotacoes futuras do python
from __future__ import annotations
# nativo para ER (usado em validacoes de CPF, CEP email e telefone)
import re
# nativo para criar classes abstratas e metodos nas subclasses
from abc import ABC, abstractmethod
# manipulacao de datas
from datetime import date, datetime, timedelta
# evitar dependencia circular em tempo de execucao (A precisa de B enquanto B precisa de A)
from typing import TYPE_CHECKING

# FLASK -> criacao e validacao de tokens de sessao seguros
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
# FLASK -> hash seguro de senhas e verificacao
from werkzeug.security import check_password_hash, generate_password_hash

from .base import (
    Entidade, AcessoNegadoError, AutenticacaoError, SenhaFracaError, StatusPedido, ValidacaoError,
    exigirTexto, textoOpcional, validarCPF, validarData, validarEmail, validarTelefone
)

# ENDEREÇO (DER: CLIENTE 1:N ENDEREÇO)
class Endereco(Entidade):
    """ 
    Representa o endereço de entrega de um cliente
    DER: ID_endereco (PK), CLIENTEUSUÁRIOID_usuário (FK), apelido (nulo), logradouro, numero, complemento (nulo), bairro, cidade, cep char(8)
    """
    def __init__(self, logradouro: str, numero: str, bairro: str, cidade: str, cep: str, complemento: str = "", apelido: str = "", id_endereco: int | None = None):   
        # Guarda a pk id_endereco
        super().__init__(id_endereco)

        # Atributos protegidos (_) -> lidos por @property
        self._logradouro = exigirTexto(logradouro, "logradouro")
        self._numero = exigirTexto(numero, "número")
        self._bairro = exigirTexto(bairro, "bairro")
        self._cidade = exigirTexto(cidade, "cidade")
        self._complemento = textoOpcional(complemento, "complemento")
        self._apelido = textoOpcional(apelido, "apelido")
        
        # Validação do cep
        # \D significa tudo que não for dígito numérico -> apaga traços, pontos, letras, espaços
        digitos = re.sub(r"\D", "", cep or "")
        if len(digitos) != 8:
            raise ValidacaoError("CEP inválido: deve conter 8 dígitos.")
        self._cep = digitos

        # FK CLIENTEUSUARIOID_usuario, o cliente pode ser criado antes de ter o ID e receber-lo após o INSERT
        self._cliente: "Cliente | None" = None

    # @property -> encapsulamento, cria um tipo de atalho de leitura
    # O endereço é imutável depois de criado, para mudar deve remover e cadastrar outro
    @property
    def logradouro(self): return self._logradouro
    @property
    def numero(self): return self._numero
    @property
    def complemento(self): return self._complemento
    @property
    def bairro(self): return self._bairro
    @property
    def cidade(self): return self._cidade
    @property
    def cep(self): return self._cep
    @property
    def apelido(self): return self._apelido

    @property
    def id_cliente(self) -> int | None:
        """Novo valor da fk para a tabela CLIENTE"""
        return self._cliente.id if self._cliente else None

    def _vincular(self, cliente: "Cliente | None") -> None:
        """Uso interno, ao adicicionar ou remover um endereço de um cliente"""
        self._cliente = cliente

    def formatado(self) -> str:
        """Retorna o endereço formatado por extenso"""
        # verifica se o cliente digitou algum complemento, caso sim, coloca uma virgula antes, caso nao, deixa vazio
        complemento = f", {self._complemento}" if self._complemento else ""
        # junta tudo em uma frase so e formata o cep colocando o traco
        return (f"{self._logradouro}, {self._numero}{complemento} - {self._bairro}, "
                f"{self._cidade} - CEP {self._cep[:5]}-{self._cep[5:]}")

    def __repr__(self) -> str:
        """representacao do texto"""
        return f"Endereco({self.formatado()})"

# VALIDAR SENHAS
class ValidadorSenha:
    """
    Classe responsável por validar a senha informada com base nos requisitos de segurança
    """
    TAMANHO_MINIMO = 8

    @classmethod
    # cls eh similar ao self, ms referencia a classe toda, permite acessar constantes
    def validar(cls, senha: str) -> None:
        """Acumula todos os problemas e lança um único erro com a lista completa"""
        # cria uma lista vazia para acumular todas as falhas que a senha apresentar
        problemas = []
        # verifica se a senha esta vazia ou se o tamanho total eh menor que o minimo, caso sim, add na lista de problemas
        if senha is None or len(senha) < cls.TAMANHO_MINIMO:
            problemas.append(f"Ter ao menos {cls.TAMANHO_MINIMO} caracteres")
        # usa ERs para procurar letras maiusculas e minusculas na senha, caso nao encontre, eh disparao um erro
        # senha or "" -> se o usuario passar um valor nulo, o codigo analisara uma string vazia
        if not re.search(r"[A-Za-z]", senha or ""):
            problemas.append("Conter letras")
        # usa ERs para verificar a presenca de numeros, se a senha noa tiver nenhum numero, o sistema lanca o aviso correspondente
        if not re.search(r"\d", senha or ""):
            problemas.append("Conter números")
        # ^ = negacao -> procura qualquer coisa que nao seja letra e nao seja numero, se nao houver caracteres especiais o problema eh registrado
        if not re.search(r"[^A-Za-z0-9]", senha or ""):
            problemas.append("conter ao menos um caractere especial (ex.: @, #, !)")
        # if problemas = se na lista de problemas houver pelo menos 1 registro significa que a senha falhou em algum requisito
        # exibe os problemas
        if problemas:
            raise SenhaFracaError("A senha deve " + ", ".join(problemas) + ".")

# USUARIO      
class Usuario(Entidade, ABC):
    """
    Superclasse que representa um usuário genérico no sistema

    DER: ID_usuario, nome, email (único), telefone (único), senha (hash), data_cadastro, ativo, cpf (único), data_nascimento
    """

    def __init__(self, nome: str, email: str, telefone: str, cpf: str, data_nascimento: date | datetime | None = None, senha_plana: str | None = None, 
        senha_hash: str | None = None, id_usuario: int | None = None, data_cadastro: datetime | None = None, ativo: bool = True):
       
        super().__init__(id_usuario)
        self._nome = exigirTexto(nome, "nome")
        self._email = validarEmail(email)
        self._telefone = validarTelefone(telefone)
        self._data_cadastro = data_cadastro or datetime.now()
        self._ativo = bool(ativo)
        self._data_nascimento = (validarData(data_nascimento, "data_nascimento") if data_nascimento else None)
        self.__cpf = validarCPF(cpf)
        # DER: "senha" guarda a senha hash, nunca a senha real
        self.__senha_hash = " "
        # Necessário olhar if/elif/else -> comentário do professor sobre utilizar autômatos
        if senha_hash:
            self.__senha_hash = senha_hash
        elif senha_plana is not None:
            self.definirSenha(senha_plana)
        else:
            raise ValidacaoError("É necessário informar uma senha")

    # Getters e setters
    @property
    def nome(self) -> str: return self._nome

    @nome.setter
    def nome(self, v: str):
        self._nome = exigirTexto(v, "nome")

    @property
    def email(self) -> str: return self._email

    @email.setter
    def email(self, v: str):
        self._email = validarEmail(v)

    @property
    def telefone(self) -> str: return self._telefone

    @telefone.setter
    def telefone(self, v: str):
        self._telefone = validarTelefone(v)

    @property
    def data_cadastro(self) -> datetime: return self._data_cadastro

    @property
    def data_nascimento(self) -> date | None:
        return self._data_nascimento

    @data_nascimento.setter
    def data_nascimento(self, v):
        self._data_nascimento = validarData(v, "data de nascimento")

    @property
    def ativo(self) -> bool: return self._ativo

    def ativar(self):
        self._ativo = True

    def desativar(self):
        self._ativo = False

    # Dados sensíveis
    @property
    def senha_hash(self) -> str:
        # Exposto apenas para gravar "senha"
        return self.__senha_hash

    @property
    def CPF_persis(self) -> str:
        # Exposto para gravar "cpf", para exibir para alguem deve-se usar obterCPF, que checa a permissão
        return self.__cpf

    def obterCPF(self, solicitante: "Usuario") -> str:
        """Só o próorio dono ou quem pode acessar dados sensíveis (admin) pode ver o CPF"""
        if solicitante is self or solicitante.podeAcessarDadosSensiveis:
            return self.__cpf
        raise AcessoNegadoError("Apenas o usuário admin pode consultar este CPF")

    # METODOS DE SENHAS -> fazer verificação com a documentacao do flask depois, adicionados para nao quebrar o codigo na parte de autenticacao
    def definirSenha(self, senha:str) -> None:
        ValidadorSenha.validar(senha)
        self.__senha_hash = generate_password_hash(senha)

    def verificarSenha(self, senha: str) -> bool:
        return check_password_hash(self.__senha_hash, senha or "")

    # Contrato
    @property
    @abstractmethod
    def perfil(self) -> str:
        """'cliente', 'funcionario' ou 'administrador'"""

    @property
    @abstractmethod
    def podeAcessarDadosSensiveis(self) -> bool:
        """Indica se o usuário pode acessar dados sensíveis"""

# CLIENTE
class Cliente(Usuario):
    """
    DER: apelido, cliente_vip, instagram (nulável), restrições_alimentares (nulável), observações (nulável), preferênicias
    """

    def __init__(self, nome: str, email: str, telefone: str, cpf: str, apelido: str = "", cliente_vip: bool = False,
        instagram: str = "", restricoes_alimentares: str = "", observacoes: str = "", preferencias: str = "",
        data_ultimo_pedido: datetime | None = None, **kwargs):

        # **kwargs passa a senha plana, a senha hash, id usuario, data nascimento, etc
        super().__init__(nome, email, telefone, cpf, **kwargs)
        # DER: apelido não é nulo, se não for informado usa o próprio nome
        self._apelido = exigirTexto(apelido or nome, "apelido")
        self._cliente_vip = bool(cliente_vip)
        # DER: NULL no DER vira None
        self._instagram = textoOpcional(instagram, "instagram")
        # Dado de saúde/segurança 
        self._restricoes_alimentares = textoOpcional(restricoes_alimentares, "restrições alimentares")
        self._observacoes = textoOpcional(observacoes, "observações", max_len=10_000)
        self._preferencias = textoOpcional(preferencias, "preferências", max_len=10_000)
        # Não está no recorte do DER: é um dado DERIVADO (último pedido do cliente na tabela de pedidos). Mantido só em memória;
        self._data_ultimo_pedido = data_ultimo_pedido
        self._enderecos: list[Endereco] = []  # Relação 1:N com ENDEREÇO

    # Implementação das propriedades abstratas
    perfil = property(lambda self: "cliente")
    podeAcessarDadosSensiveis = property(lambda self: False)
    
    @property
    def apelido(self) -> str: return self._apelido
    @apelido.setter
    def apelido(self, v: str): self._apelido = exigirTexto(v, "apelido")

    @property
    def cliente_vip(self) -> bool: return self._cliente_vip

    @property
    def instagram(self) -> str | None: return self._instagram
    @instagram.setter
    def instagram(self, v): self._instagram = textoOpcional(v, "instagram")

    @property
    def restricoes_alimentares(self) -> str | None: return self._restricoes_alimentares
    @restricoes_alimentares.setter
    def restricoes_alimentares(self, v):
        self._restricoes_alimentares = textoOpcional(v, "restrições alimentares")

    @property
    def observacoes(self) -> str | None: return self._observacoes
    @observacoes.setter
    def observacoes(self, v): self._observacoes = textoOpcional(v, "observações", max_len=10_000)

    @property
    def preferencias(self) -> str | None: return self._preferencias
    @preferencias.setter
    def preferencias(self, v): self._preferencias = textoOpcional(v, "preferências", max_len=10_000)

    @property
    def data_ultimo_pedido(self): return self._data_ultimo_pedido

    @property
    def enderecos(self) -> tuple[Endereco, ...]:
        # Devolve uma cópia imutável: ninguém altera a lista interna por fora.
        return tuple(self._enderecos)       

    # Endereços
    def adicionarEndereco(self, endereco: Endereco) -> None:
        # Preenche a fk id_cliente do endereco
        endereco._vincular(self)
        self._enderecos.append(endereco)

    def removerEndereco(self, endereco: Endereco) -> None:
        if endereco not in self._enderecos:
            raise ValidacaoError("Este endereço não pertence a este cliente")
        self._enderecos.remove(endereco)
        # Desfaz o vínculo
        endereco._vincular(None)

    # Regras de negócio
    def registrarPedido(self, data: datetime) -> None:
        self._data_ultimo_pedido = data

    def promoverVip(self) -> None: self._cliente_vip = True
    def removerVip(self) -> None: self._cliente_vip = False

    # Privacidade
    def acessoAosDados(self, solicitante: Usuario) -> dict: # retorno do tipo chave valor
        """Filtra o que cada perfil pode ver sobre este cliente"""
        if solicitante is self or solicitante.podeAcessarDadosSensiveis:
            return {"nome": self._nome, "apelido": self._apelido, "email": self._email,
                    "telefone": self._telefone, "cpf": self.obterCPF(solicitante),
                    "data_nascimento": self._data_nascimento, "vip": self._cliente_vip,
                    "instagram": self._instagram,
                    "restricoes_alimentares": self._restricoes_alimentares,
                    "observacoes": self._observacoes, "preferencias": self._preferencias,
                    "enderecos": [e.formatado() for e in self._enderecos]}

        # isinstance serve para testar se uma var ou objeto pertence a um tipo de dado ou classe antes de exc o código
        if isinstance(solicitante, Funcionario):
            return {"apelido": self._apelido, "telefone": self._telefone,
                    "restricoes_alimentares": self._restricoes_alimentares,
                    "enderecos": [e.formatado() for e in self._enderecos]}
        raise AcessoNegadoError("Usuário sem permissão para ver os dados deste cliente")
    
class Funcionario(Usuario):
    """
    DER: cargo, data_contratação
    """
    def __init__(self, nome: str, email: str, telefone: str, cpf: str, cargo: str,
        data_nascimento: date | datetime, data_contratacao: date | datetime | None = None, **kwargs):
        # DER: data_nascimento é nullável em USUÁRIO, mas para funcionário o sistema continua esige
        super().__init__(nome, email, telefone, cpf, data_nascimento=data_nascimento, **kwargs)
        self._cargo = exigirTexto(cargo, "cargo")
        self._data_contratacao = validarData(data_contratacao or date.today(), "data de contratação")

    perfil = property(lambda self: "funcionario")
    podeAcessarDadosSensiveis = property(lambda self: False)

    @property
    def cargo(self) -> str: return self._cargo
    @cargo.setter
    def cargo(self, v: str): self._cargo = exigirTexto(v, "cargo")
    @property
    def data_contratacao(self): return self._data_contratacao

    # Ainda não foram implementadas as classes Pedido e Estoque, este trecho de código é uma ideia de como poderiam funcionar estes métodos
    def atualizarStatusPedido(self, pedido: "Pedido", novo_status: StatusPedido) -> None:
        """Avança o pedido na fila de produção"""
        pedido.avancarStatus(novo_status)
 
    def consultarEstoque(self, estoque: "Estoque") -> list[dict]:
        """Consulta o resumo do estoque"""
        return estoque.resumo()

class Administrador(Usuario):
    """DER: nivel_privilegio, acesso_financeiro"""
 
    def __init__(self, nome: str, email: str, telefone: str, cpf: str, nivel_privilegio: str = "total", acesso_financeiro: bool = True, **kwargs):

        super().__init__(nome, email, telefone, cpf, **kwargs)
        self._nivel_privilegio = exigirTexto(nivel_privilegio, "nível de privilégio")
        self._acesso_financeiro = bool(acesso_financeiro)
 
    perfil = property(lambda self: "administrador")
    # Único perfil com acesso a dados sensíveis
    podeAcessarDadosSensiveis = property(lambda self: True)

    @property
    def nivelPrivilegio(self) -> str:
        return self._nivel_privilegio

    @property
    def acessoFinanceiro(self) -> bool:
        return self._acesso_financeiro

    def ajustarEstoque(self, estoque: "Estoque", ingrediente: "Ingrediente", nova_quantidade: float, motivo: str) -> None:
        """Ajusta manualmente a quantidade de um ingrediente no estoque"""
        estoque.ajustarManual(ingrediente, nova_quantidade, motivo)

    def consultarCPFCliente(self, cliente: Cliente) -> str:
        return cliente.obterCPF(self)

    def gerar_relatorio_reposicao(self, recomendador, estoque, historico):
        """Aciona o modulo de recomendacao de compras"""
        if not self._acesso_financeiro:
            raise AcessoNegadoError("Este administrador não possui acesso a relatórios financeiros.")
        return recomendador.recomendar(estoque, historico)

# AUTENTICACAO
class Autenticacao:
    """Cuida do login dos usuários, controla tentativas de senha incorretas e cria token para manter a sessão do usuário autenticado"""
    # Encontra o usuário -> Confere a senha -> Protege o login -> Cria e valida um token

    MAX_TENTATIVAS = 5
    TEMPO_BLOQUEIO = timedelta(minutes=15)
    VALIDADE_TOKEN_SEGUNDOS = 8 * 3600 # 8h

    def __init__(self, repositorio_usuarios, chave_secreta: str):
        if not chave_secreta or len(chave_secreta) < 16:
            raise ValidacaoError(
                "A chave secreta deve ter ao menos 16 caracteres"
                ) # .env
        
        self._repo = repositorio_usuarios

        # Biblioteca ItsDangerous
        # Permite transformar dados em um token assinado e verificar se esse token permanece válido
        # salt = confeitaria auth ---> valor adiicional que separa o uso dessa chave para outros usos da mesma chave
        self._serializer = URLSafeTimedSerializer(
            chave_secreta, 
            salt="confeitaria-auth"
            )
        
        # Controle de tentativas
        # self._falhas ={} cria um dicionario vazio
        # P dicionário vai guardar info sobre tentativas de login de cada identificador
        # Exemplo: "x@email.com": (3, None) ou y@email.com: (5, tempo_de_bloqueio)
        # O dicionario fica na memoria do programa
        self._falhas: dict[str, tuple[int, datetime | None]] = {}
        self._hash_isca = generate_password_hash("Isca contra enumeração de usuários")
    
    def _localizar(self, identificador: str) -> Usuario | None:
        """Busca por e-mail ou por apelido de usuário"""
        ident = (identificador or "").strip().lower()
        return self._repo.buscar_por(
            # email do usuário = ao identificador? ou apelido do usuário = ao identificador?
            lambda u: u.email == ident or (getattr(u, "apelido", "") or "").lower() == ident)

    # Recebe identificador e senha para tentar autenticar o usuário
    # Se as credenciais forem válidas e a conta estiver ativa, retorna o usuário
    # Se não, registra a falha e lança exceção
    def autenticar(self, identificador: str, senha: str) -> Usuario:
        """Valida as credenciais e aplica bloqueio temporário após excesso de falhas"""
        chave = (identificador or "").strip().lower()
        # 'get' procura a chave no dicionário
        # Exemplo: sel._falhas[x@email.com] = (3, None) devolve tentativas=3 e bloqueado_ate=None
        tentativas, bloqueado_ate = self._falhas.get(chave, (0, None))

        # Verifica se existe bloqueio ativo e compara o horário atual com o fim do bloqueio
        if bloqueado_ate and datetime.now() < bloqueado_ate:
            raise AutenticacaoError("Muitas tentativas incorretas, tente novamente em alguns minutos")

        # Reinicia o contador após o término do bloqueio
        tentativas = 0
        bloqueado_ate = None

        # Procura o usuário
        usuario = self._localizar(identificador)
        if usuario:
            # Confere a senha digitada usando a verificacao do hash
            # Senha correta: valido = True; senha incorreta: valido = False
            valido = usuario.verificarSenha(senha)
        else:
            check_password_hash(self._hash_isca, senha or "")  # normaliza o tempo
            valido = False
 
        # Senha inválida ou conta inativa: login recusado
        if not valido or not usuario.ativo:
            tentativas += 1
            # Se o número de tentativas for pelo menos 5, define o bloqueio para 15min a partir do horário atual
            # Caso contrário, guarda None
            bloqueio = datetime.now() + self.TEMPO_BLOQUEIO if tentativas >= self.MAX_TENTATIVAS else None
            self._falhas[chave] = (tentativas, bloqueio)
            # Mensagem genérica: não revela se o e-mail existe nem se a conta está inativa
            raise AutenticacaoError("E-mail/usuário ou senha incorretos.")
        # Se o login der certo, .pop remove do dicionário o registro de falhas daquele identificador
        self._falhas.pop(chave, None)
        return usuario
 
    def gerar_token(self, usuario: Usuario) -> str:
        """Token assinado com o id e o perfil do usuário."""
        return self._serializer.dumps({"uid": usuario.id, "perfil": usuario.perfil})
 
    def validar_token(self, token: str) -> dict:
        """Confere assinatura e validade (8h) do token."""
        try:
            return self._serializer.loads(token, max_age=self.VALIDADE_TOKEN_SEGUNDOS)
        except SignatureExpired as exc:
            raise AutenticacaoError("Sessão expirada. Faça login novamente.") from exc
        except BadSignature as exc:
            raise AutenticacaoError("Sessão inválida.") from exc