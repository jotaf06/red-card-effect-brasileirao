// Números lidos das tabelas geradas pelo pipeline (reports/tabelas/).
// Nenhum resultado é digitado à mão: relatório e slides importam este arquivo.
// Compilar a partir da raiz: typst compile --root . presentation/<arquivo>.typ

#let tabela(nome) = csv("/reports/tabelas/" + nome + ".csv", row-type: dictionary)

// Inteiro com separador de milhar ("30814" -> "30.814").
#let milhar(s) = {
  let s = str(s)
  let neg = s.starts-with("-")
  if neg { s = s.slice(1) }
  let saida = ""
  while s.len() > 3 {
    saida = "." + s.slice(s.len() - 3) + saida
    s = s.slice(0, s.len() - 3)
  }
  (if neg { "−" } else { "" }) + s + saida
}

// Número com d casas decimais e vírgula decimal.
#let fmt(x, d: 2) = {
  let r = calc.round(float(x), digits: d)
  let partes = str(calc.abs(r)).split(".")
  let frac = if partes.len() > 1 { partes.at(1) } else { "" }
  while frac.len() < d { frac += "0" }
  (if r < 0 { "−" } else { "" }) + milhar(partes.at(0)) + (if d > 0 { "," + frac } else { "" })
}

// Percentual a partir de proporção (0,062 -> "6,2").
#let pct(x, d: 1) = fmt(float(x) * 100, d: d)

// p-valor: "< 0,001" abaixo do limiar; senão 3 casas.
#let pfmt(p) = {
  let p = float(p)
  if p < 0.001 { "< 0,001" } else { "= " + fmt(p, d: 3) }
}

// IRR com IC: "1,39 (IC 95%: 1,19–1,64)".
#let com_ic(linha, valor: "irr") = [#fmt(linha.at(valor)) (IC 95%: #fmt(linha.ic95_inf)–#fmt(linha.ic95_sup))]

// Resumos chave–valor.
#let resumo = tabela("resumo_base")
#let resumo_features = tabela("features_resumo")
#let chave(t, k) = t.find(l => l.chave == k).valor
#let n(k) = {
  let s = chave(resumo, k)
  if s.contains(".") { s.replace(".", ",") } else { milhar(s) }
}
#let nf(k) = {
  let s = chave(resumo_features, k)
  if s.contains(".") { fmt(s, d: 1) } else { milhar(s) }
}

// Elo.
#let elo = tabela("elo_parametros")
#let elo_escolhido = elo.find(l => l.escolhido == "True")
#let elo_baseline = elo.find(l => l.margem == "baseline_frequencias")

// H3.
#let h3_irr = tabela("h3_irr")
#let irr(modelo, termo) = h3_irr.find(l => l.modelo == modelo and l.termo == termo)
#let h3_testes = tabela("h3_testes")
#let h3_teste(prefixo) = h3_testes.find(l => l.teste.starts-with(prefixo))
#let h3_taxas = tabela("h3_taxas_estado")
#let taxa_estado(estado, tipo: "todos") = h3_taxas.find(l => l.estado == estado and l.tipo == tipo)

// H5.
#let h5_testes = tabela("h5_testes")
#let h5_teste(prefixo) = h5_testes.find(l => l.teste.starts-with(prefixo))
#let h5_faixa = tabela("h5_taxas_faixa")
#let taxa_faixa(faixa, tipo: "todos") = h5_faixa.find(l => l.faixa_rotulo == faixa and l.tipo == tipo)
#let h5_fina = tabela("h5_taxas_faixa_fina")
#let taxa_fina(faixa) = h5_fina.find(l => l.faixa_fina_rotulo == faixa)
#let h5_formacao = tabela("h5_posicao_formacao")
#let formacao(posicao, variante: "principal") = h5_formacao.find(l => l.posicao == posicao and l.variante == variante)
#let h5_cartao = tabela("h5_posicao_cartao")
#let cartao(posicao) = h5_cartao.find(l => l.posicao == posicao)
#let h5_pares = tabela("h5_posicao_cartao_pares")
#let par_posicoes(a, b) = h5_pares.find(l => l.posicao_a == a and l.posicao_b == b)
#let h5_tendencia = tabela("h5_tendencia")

// H1, H2, H4: efeito do vermelho no resultado.
#let h1_testes = tabela("h1_testes")
#let h1_teste(prefixo) = h1_testes.find(l => l.teste.starts-with(prefixo))
#let h1_att = tabela("h1_pareamento_att")
#let att(grupo) = h1_att.find(l => l.grupo == grupo)
#let h1_equilibrio = tabela("h1_pareamento_equilibrio").at(0)
#let h1_gols = tabela("h1_gols_irr")
#let gols_irr(modelo, termo) = h1_gols.find(l => l.modelo == modelo and l.termo == termo)
#let h1_custo = tabela("h1_custo_minuto")
#let custo(m, saldo, lado) = h1_custo.find(l => l.landmark == str(m) and l.saldo_punido == str(saldo) and l.lado_punido == lado)
#let h1_ajuste = tabela("h1_modelo_estado_ajuste")
#let estado_ajuste(modelo) = h1_ajuste.find(l => l.modelo == modelo)

// Comparação de modelos (teste 2022–2024).
#let modelos_metricas = tabela("modelos_metricas")
#let metrica(modelo, sub: "todos os landmarks") = modelos_metricas.find(l => l.modelo == modelo and l.subconjunto == sub)
#let modelos_dif = tabela("modelos_dif_log_loss")
#let dif_ll(modelo) = modelos_dif.find(l => l.modelo == modelo)

// Valor com IC para qualquer coluna: "−0,30 (IC 95%: −0,36 a −0,24)".
#let val_ic(linha, valor, d: 2) = [#fmt(linha.at(valor), d: d) (IC 95%: #fmt(linha.ic95_inf, d: d) a #fmt(linha.ic95_sup, d: d))]
#let pct_var(x) = { let v = (float(x) - 1) * 100; (if v > 0 { "+" } else { "" }) + fmt(v, d: 0) + "%" }
#let fmt_ou(x, d: 3) = if x == "" or x == "nan" { "—" } else { fmt(x, d: d) }
#let curvas_modelos = tabela("modelos_custo_curvas")
#let curva(m, saldo, lado) = curvas_modelos.find(l => l.landmark == str(m) and l.saldo_punido == str(saldo) and l.lado_punido == lado)
