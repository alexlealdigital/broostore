"""Modelos SQLAlchemy — UM conjunto só, compartilhado por web e worker.

Unificação dos dois conjuntos que existiam em app.py e worker.py (superset):
mesmos nomes de tabelas e colunas, SEM mudança de schema.

  * Cobranca: versão do app.py (external_reference único, telefone, valor_original,
    vendedor, cupom). O worker usava uma versão reduzida das mesmas colunas.
  * ChaveLicenca: colunas do app.py (inclui ``ativa_no_app``) + relationship
    ``produto`` (backref ``chaves``) que existia só no worker.
  * Sale: existia só no worker.
"""
from datetime import date, datetime

from .extensions import db


class Vendedor(db.Model):
    __tablename__ = "vendedores"
    codigo_ranking = db.Column(db.String(50), primary_key=True)
    nome_vendedor = db.Column(db.String(200), nullable=False)
    email_contato = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            "codigo_ranking": self.codigo_ranking,
            "nome_vendedor": self.nome_vendedor
        }


class Cupom(db.Model):
    __tablename__ = "cupons"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='percentual')  # 'percentual' ou 'valor_fixo'
    valor = db.Column(db.Float, nullable=False)  # 70 (%) ou 10 (R$)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=True)  # NULL = todos
    produto = db.relationship('Produto')
    valido_de = db.Column(db.Date, default=date.today)
    valido_ate = db.Column(db.Date, nullable=True)
    usos_maximos = db.Column(db.Integer, nullable=True)  # NULL = ilimitado
    usos_atuais = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "tipo": self.tipo,
            "valor": self.valor,
            "produto_id": self.produto_id,
            "valido_ate": self.valido_ate.isoformat() if self.valido_ate else None,
            "usos_maximos": self.usos_maximos,
            "usos_atuais": self.usos_atuais,
            "ativo": self.ativo
        }

    def esta_valido(self):
        """Verifica se o cupom está ativo e dentro da validade"""
        if not self.ativo:
            return False, "Cupom inativo"

        hoje = date.today()
        if self.valido_de and hoje < self.valido_de:
            return False, "Cupom ainda não está válido"
        if self.valido_ate and hoje > self.valido_ate:
            return False, "Cupom expirado"

        if self.usos_maximos is not None and self.usos_atuais >= self.usos_maximos:
            return False, "Limite de usos atingido"

        return True, "Válido"

    def calcular_desconto(self, valor_original):
        """Calcula o valor com desconto aplicado"""
        if self.tipo == 'percentual':
            desconto = valor_original * (self.valor / 100)
        else:  # valor_fixo
            desconto = min(self.valor, valor_original)  # Não permite valor negativo

        valor_final = max(0, valor_original - desconto)
        return {
            "valor_original": valor_original,
            "desconto": desconto,
            "valor_final": valor_final,
            "percentual_aplicado": self.valor if self.tipo == 'percentual' else (desconto / valor_original * 100)
        }


class Cobranca(db.Model):
    __tablename__ = "cobrancas"
    id = db.Column(db.Integer, primary_key=True)
    external_reference = db.Column(db.String(100), unique=True, nullable=False)
    cliente_nome = db.Column(db.String(200), nullable=False)
    cliente_email = db.Column(db.String(200), nullable=False)
    cliente_telefone = db.Column(db.String(20), nullable=True)
    valor = db.Column(db.Float, nullable=False)
    valor_original = db.Column(db.Float, nullable=True)  # Valor antes do desconto
    # Estados: pending/in_process/rejected... (Mercado Pago) -> "approved" (pago e
    # cumprido, e-mail ainda pendente) -> "delivered" (e-mail enviado).
    status = db.Column(db.String(50), default="pending", nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=True)
    produto = db.relationship('Produto')

    chave_usada = db.relationship('ChaveLicenca', backref='cobranca_rel', uselist=False)

    vendedor_codigo = db.Column(db.String(50), db.ForeignKey('vendedores.codigo_ranking'), nullable=True)
    vendedor = db.relationship('Vendedor', backref='vendas')

    cupom_id = db.Column(db.Integer, db.ForeignKey('cupons.id'), nullable=True)
    cupom = db.relationship('Cupom')
    observacoes = db.Column(db.Text, nullable=True)  # JSON com endereco para produto fisico

    def to_dict(self):
        return {
            "id": self.id,
            "external_reference": self.external_reference,
            "cliente_nome": self.cliente_nome,
            "cliente_email": self.cliente_email,
            "cliente_telefone": self.cliente_telefone,
            "valor": self.valor,
            "valor_original": self.valor_original,
            "status": self.status,
            "data_criacao": self.data_criacao.isoformat() if self.data_criacao else None,
            "vendedor_codigo": self.vendedor_codigo,
            "cupom_id": self.cupom_id
        }


class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    link_download = db.Column(db.String(500), nullable=False)
    tipo = db.Column(db.String(50), default="ebook", nullable=False)


class ChaveLicenca(db.Model):
    __tablename__ = "chaves_licenca"
    id = db.Column(db.Integer, primary_key=True)
    chave_serial = db.Column(db.String(100), unique=True, nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    produto = db.relationship('Produto', backref=db.backref('chaves', lazy=True))
    vendida = db.Column(db.Boolean, default=False, nullable=False)
    vendida_em = db.Column(db.DateTime, nullable=True)
    cobranca_id = db.Column(db.Integer, db.ForeignKey('cobrancas.id'), unique=True, nullable=True)
    cliente_email = db.Column(db.String(200), nullable=True)
    ativa_no_app = db.Column(db.Boolean, default=False, nullable=False)


class Sale(db.Model):
    """Venda registrada localmente (existia só no worker.py)."""
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ---------- ASSINATURA / LICENÇA (BrooStock) ----------
class PlanoAssinatura(db.Model):
    __tablename__ = "planos_assinatura"
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), primary_key=True)
    dias = db.Column(db.Integer, nullable=False)            # 30, 365...
    rotulo = db.Column(db.String(50), nullable=True)        # 'mensal' / 'anual'


class Licenca(db.Model):
    __tablename__ = "licencas"
    id = db.Column(db.Integer, primary_key=True)
    cliente_email = db.Column(db.String(200), nullable=False, index=True)
    plano = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(30), default="ativa", nullable=False)
    inicia_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expira_em = db.Column(db.DateTime, nullable=False)
    ultimo_pagamento_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cobranca_id = db.Column(db.Integer, db.ForeignKey('cobrancas.id'), nullable=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=True)
    ultimo_aviso = db.Column(db.String(20), nullable=True)  # '7d' | '2d' | 'expirado' | None
