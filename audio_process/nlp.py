import re
import json
from datetime import date
import aiofiles

class ProcessadorFrase:
    CATEGORIAS = ["CARTAO", "ALUGUEL", "COMIDA", "MERCADO", "ROLES", "OUTROS", "COMBUSTIVEL", "CONTAS"]

    def __init__(self):
        pass

    async def processar(self, frase: str) -> dict:
        resultado = {
            "frase": frase,
            "valor": None,
            "local": "Desconhecido",
            "data": str(date.today()),
            "categoria": "OUTROS"
        }

        padrao_valor = re.search(r"(\d+[,.]?\d*)\s*(reais|rs|r\$)?", frase, re.IGNORECASE)
        if padrao_valor:
            valor_str = padrao_valor.group(1).replace(",", ".")
            try:
                resultado["valor"] = float(valor_str)
            except ValueError:
                pass

        for cat in self.CATEGORIAS:
            if cat.lower() in frase.lower():
                resultado["categoria"] = cat
                break

        valor_idx = padrao_valor.start() if padrao_valor else len(frase)
        categoria_idx = min(
            [frase.lower().find(cat.lower()) for cat in self.CATEGORIAS if cat.lower() in frase.lower()] + [len(frase)]
        )
        possivel_local = frase[:min(valor_idx, categoria_idx)].strip()

        if possivel_local:
            resultado["local"] = possivel_local

        return resultado

    async def processar_de_json(self, caminho_json: str) -> dict:
        async with aiofiles.open(caminho_json, "r", encoding="utf-8") as f:
            conteudo = await f.read()
            data = json.loads(conteudo)

        if len(data["resultados"]) > 0 :
            frase = data["resultados"][0]["alternativas"][0]["transcricao"]
            return await self.processar(frase)
        return None



# Permite uso como script e como módulo importável
def processar_frase_de_json(caminho_json: str):
    import asyncio
    pf = ProcessadorFrase()
    return asyncio.run(pf.processar_de_json(caminho_json))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python nlp.py <caminho_json>")
        exit(1)
    resultado = processar_frase_de_json(sys.argv[1])
    print(resultado)
