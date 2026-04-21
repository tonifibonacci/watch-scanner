# ⌚ Watch Deal Scanner

Scanner automático de relógios subvalorizados no **Vinted PT** e **Vinted FR**.  
Corre de 2 em 2 horas via GitHub Actions e publica um dashboard HTML.




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
