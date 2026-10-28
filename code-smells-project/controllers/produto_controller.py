from controllers.erros import NotFoundError, ValidationError
from controllers.validacao import eh_numero, exige_objeto
from database import get_db, transacao
from models.produto_model import ProdutoModel

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def listar():
    return ProdutoModel.get_all(get_db())


def buscar(produto_id):
    return _existente(get_db(), produto_id)


def buscar_com_filtros(termo, categoria, preco_min, preco_max):
    return ProdutoModel.search(
        get_db(),
        termo,
        categoria,
        _preco_opcional(preco_min, "preco_min"),
        _preco_opcional(preco_max, "preco_max"),
    )


def criar(dados):
    campos = _validar(exige_objeto(dados))
    db = get_db()
    with transacao(db):
        produto_id = ProdutoModel.create(db, **campos)
    return {"id": produto_id}


def atualizar(produto_id, dados):
    db = get_db()
    _existente(db, produto_id)
    campos = _validar(exige_objeto(dados))
    with transacao(db):
        ProdutoModel.update(db, produto_id, **campos)


def deletar(produto_id):
    db = get_db()
    _existente(db, produto_id)
    with transacao(db):
        ProdutoModel.delete(db, produto_id)


def _existente(db, produto_id):
    produto = ProdutoModel.get_by_id(db, produto_id)
    if produto is None:
        raise NotFoundError("Produto nao encontrado")
    return produto


def _validar(dados):
    for campo, mensagem in (("nome", "Nome é obrigatório"), ("preco", "Preço é obrigatório"), ("estoque", "Estoque é obrigatório")):
        if campo not in dados:
            raise ValidationError(mensagem)

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", "geral")

    if not isinstance(nome, str) or not isinstance(descricao, str):
        raise ValidationError("Nome e descrição devem ser textos")
    if not eh_numero(preco):
        raise ValidationError("Preço deve ser numérico")
    if not isinstance(estoque, int) or isinstance(estoque, bool):
        raise ValidationError("Estoque deve ser inteiro")
    if preco < 0:
        raise ValidationError("Preço nao pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque nao pode ser negativo")
    if len(nome) < 2:
        raise ValidationError("Nome muito curto")
    if len(nome) > 200:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


def _preco_opcional(valor, campo):
    if not valor:
        return None
    try:
        return float(valor)
    except ValueError:
        raise ValidationError(f"{campo} deve ser numérico")
