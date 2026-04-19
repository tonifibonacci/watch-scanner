# ⌚ Watch Deal Scanner

Scanner automático de relógios subvalorizados no **Vinted PT** e **Vinted FR**.  
Corre de 2 em 2 horas via GitHub Actions e publica um dashboard HTML.

## 🚀 Setup (5 minutos, sem instalar nada)

### 1. Criar o repositório no GitHub
1. Vai a [github.com](https://github.com) e cria conta se não tiveres
2. Clica **New repository**
3. Nome: `watch-scanner` · Visibilidade: **Public** (necessário para GitHub Pages grátis)
4. Clica **Create repository**

### 2. Fazer upload dos ficheiros
Na página do repositório clica **uploading an existing file** e faz upload de:
- `scraper.py`
- `.github/workflows/scan.yml` (cria a pasta `.github/workflows/` manualmente)

Ou usa o GitHub Desktop (mais fácil).

### 3. Ativar GitHub Pages
1. Vai a **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `gh-pages` · Folder: `/ (root)`
4. Clica **Save**

### 4. Correr o primeiro scan
1. Vai a **Actions → Watch Deal Scanner**
2. Clica **Run workflow → Run workflow**
3. Aguarda ~5 minutos

### 5. Ver o dashboard
O teu dashboard fica disponível em:
```
https://SEU_USERNAME.github.io/watch-scanner/
```

---

## ⚙️ Personalizar keywords e preços

Edita o ficheiro `scraper.py`, secção `PRICE_DB`:

```python
PRICE_DB = {
    "nome da pesquisa": (max_compra_excelente, max_compra_bom, preco_venda_estimado),
    # Exemplo:
    "seiko kinetic": (30, 80, 130),
    #  ↑ Abaixo de €30 = EXCELENTE
    #       ↑ Entre €30-80 = BOM NEGÓCIO
    #              ↑ Vender a ~€130 no Chrono24
}
```

---

## 📊 Lógica de classificação

| Rating | Condição |
|--------|----------|
| 🔥 EXCELENTE | Preço ≤ min_buy |
| ✅ BOM | Preço ≤ max_buy E margem ≥ 40% |
| ⚠️ RAZOÁVEL | Preço ≤ max_buy mas margem < 40% |
| ❌ CARO | Preço > max_buy |

---

## ⚠️ Notas

- A Vinted pode bloquear pedidos ocasionalmente — é normal, o próximo scan funciona
- Os preços de venda são estimativas baseadas em Chrono24/eBay — **verifica sempre antes de comprar**
- O GitHub Actions gratuito tem 2000 minutos/mês — mais que suficiente para este uso
