# RH Analytics

Painel local de RH com dados sincronizados do Notion, indicadores por competência, importação de ponto, geração de planilhas e auditorias.

## Iniciar

Requer Python 3.12 ou superior e Node.js compatível com o projeto. Use um ambiente Python isolado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
cd front-rh
npm ci
npm run dev
```

Acesse http://localhost:5173. O front encaminha `/api` ao backend. `RH_API_TARGET` altera o destino do proxy. `VITE_API_URL` permite definir outro endereço de API; prefira servir o front e a API na mesma origem.

## Configuração privada e acesso

`config.local.json` contém o token do Notion, hashes das senhas e regras da empresa. Não versionar, compartilhar ou colocar esta configuração em diretório público. O arquivo real foi migrado preservando os usuários existentes. Os três perfis mantêm as permissões atuais.

As sessões expiram em oito horas e são verificadas no servidor. Logout invalida a sessão. O login limita tentativas por endereço. Para trocar uma senha, execute `python gerenciar_acesso.py` e reinicie o backend. O script invalida as sessões anteriores daquele usuário. As senhas anteriores foram preservadas como hashes para não bloquear o acesso; recomenda-se substituí-las pelo procedimento local.

O token que anteriormente estava no código precisa ser revogado e substituído na conta do Notion. Depois atualize `notion_token` na configuração privada, ou use a variável `NOTION_TOKEN`, e reinicie o backend. Essa rotação não é realizada pelo aplicativo. A verificação HTTPS permanece ligada e usa os certificados confiáveis do sistema ([Truststore](https://truststore.readthedocs.io/en/latest/)); em redes com certificado corporativo, configure a cadeia confiável por `REQUESTS_CA_BUNDLE`.

Variáveis disponíveis: `RH_DB_PATH`, `RH_CONFIG`, `RH_ORIGINS` (origens separadas por vírgula), `RH_SECURE_COOKIE=true` para publicação com HTTPS. O padrão atende apenas os endereços locais conhecidos. A instalação foi preparada para uso local; exposição na rede exige HTTPS e origem configurada.

## Indicadores e limites do histórico

- Competência: dia 25 do mês anterior até dia 24 do selecionado, inclusive. Movimentações futuras não são contadas como realizadas.
- Admissões: campo `Data de admissão`, independentemente do status atual; identidade pela página do Notion.
- Quadro no fim do período: admitidos até a data de corte, sem desligamento até essa data. Na competência em andamento, o corte é hoje.
- Turnover: preservada a definição do projeto, `desligamentos / quadro ao final do período × 100`. Cartão e gráfico usam o mesmo corte e denominador histórico. Sem denominador, mostra `N/D`.
- Atestados: `Data de Entrega`. Advertências: `Data da Advertência`. Avaliações: `Data da Avaliação`. Todas essas contagens usam 25 a 24.
- Setores históricos usam o cadastro disponível e o setor do desligamento quando informado. Transferências e contratos antigos ausentes da base não podem ser reconstruídos. Registros com admissão inválida ou desligamento sem data vinculada geram avisos; não são presumidos ativos.
- Comparações são diferenças absolutas em relação à competência anterior. Competências abertas são parciais.
- Os três cartões principais permitem abrir os registros considerados. Alertas de férias existentes são estimativas por tempo de casa, sem histórico completo de férias; devem ser conferidos pelo RH.

## Sincronização

`POST /api/sincronizar` inicia uma única execução; `GET /api/sincronizar/status` informa o andamento. Todas as páginas de todas as bases precisam terminar antes da publicação em uma transação SQLite. Falhas preservam o conjunto anterior. Há tentativas limitadas para erros temporários e limite de chamadas. A tela mostra a última atualização e avisa após 24 horas.

## Folha, regras e importações

Cada fechamento guarda usuário, horário e registros em `folha_versoes`. O primeiro novo fechamento preserva também os registros legados daquela competência. O histórico pode ser consultado e baixado no painel de ponto. Um envio vazio, inválido ou com nome duplicado é recusado antes de alterar a folha atual.

O divisor de horas, percentuais de bônus e exceções de ponto ficam em `rules` da configuração privada. Os valores da empresa foram preservados; alterações exigem validação do RH. Salário ausente não recebe mais um valor inventado. Correspondências aproximadas em bônus que antes escolhiam o primeiro nome agora exigem identificação revisada. A importação de ponto usa o Código interno do Notion para vincular o código SAP e só recorre ao nome completo quando único. Outras importações ainda dependem do formato dos arquivos e de nomes quando não há matrícula utilizável: não constituem uma migração completa de todos os arquivos legados para ID.

Os parsers de arquivos legados foram mantidos. Antes de fechar uma folha real, confira os resultados contra os arquivos originais e resolva registros sem identificação. O cadastro de desempenho atual deve ser alinhado às competências usadas pelo gráfico; campos ausentes não representam uma nota validada.

## Estrutura

`main.py` monta as rotas. `rh/security.py`, `sync.py`, `metrics.py`, `payroll.py`, `rules.py` concentram as regras principais. `ponto.py`, `planilhas.py`, `auditoria.py` e `dashboard.py` separam as áreas; `core.py` reúne adaptadores legados compartilhados. `models.py` é um modelo SQLModel experimental, não usado pelo aplicativo atual.

O front centraliza as requisições em `src/api.ts`, o carregamento em `src/hooks/useDashboard.ts` e os novos componentes em `src/components`. A página principal ainda contém telas legadas que podem ser extraídas gradualmente.

## Verificação

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd front-rh
npm run build
```

Os testes usam um banco temporário e respostas fictícias do Notion. Não alteram a base real. Verificam autenticação, expiração/logout, origem, limites de competência, nomes repetidos, preservação do cache e versões de folha. A interface foi conferida com dados de demonstração.

## Backup e Git

Execute `python backup.py` antes de fechar competências e antes de atualizar. Para restaurar, pare o servidor, preserve a situação atual com outro backup e recupere o banco e a configuração do backup escolhido. Reinicie e confira a competência.

Bancos, documentos de RH, credenciais e arquivos gerados não devem ser acompanhados pelo Git. Removê-los do acompanhamento atual não apaga cópias em commits antigos. O histórico Git não foi reescrito automaticamente; revogue as credenciais expostas e trate cópias antigas antes de compartilhar o repositório.

Bancos, documentos de RH e caches deixaram de ser acompanhados nesta atualização do repositório. A cópia original da Área de Trabalho pode continuar indicando esses arquivos como acompanhados; nesse caso, execute `limpar_git.py` com seu usuário do Windows. Arquivos locais e commits antigos foram preservados.
