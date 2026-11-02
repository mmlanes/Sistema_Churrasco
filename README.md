# 🔥 Calculadora e Sistema de Gestão de Churrasco

Sistema completo desenvolvido em Python com [Streamlit](https://streamlit.io/) para planejamento, cálculo automático de insumos, gestão de colaboradores e tarefas, controle de fluxo de caixa com fotos de comprovantes e emissão de relatórios em PDF.

---

## 🌟 Principais Recursos

### 1. Gestão de Múltiplos Eventos com Isolamento Total
- Criação de eventos com nomes identificadores (ex: `"3º ELE 2025"`, `"Natal 2024"`, `"Formatura 2026"`).
- **Isolamento de Base de Dados por Pastas:** Cada evento possui sua própria pasta em `data/events/{event_id}/`, armazenando seus próprios arquivos JSON e imagens de cupons e fornecedores.
- **Clonagem e Aproveitamento de Cadastros:** É possível clonar consumíveis, receitas, fornecedores e modelos de tarefas de qualquer evento anterior para um novo evento, sem manter vínculos ou dependências ativas.
- **Carga Inicial Automática:** O evento demonstrativo `"Churrasco 3º ELE 2025"` é importado automaticamente a partir da planilha fornecida `Gastos com churrasco - 3º ELE 2025.xlsx`.

### 2. Perfis de Acesso e Auditoria
- **👑 Organizador Master:** Controle total do sistema, aprovação de sugestões, gestão de usuários e eventos (mínimo de 1 administrador garantido por regra de segurança).
- **🛠️ Colaboradores:** Podem alterar valores, atualizar o progresso de suas tarefas, registrar gastos e anexar comprovantes.
- **👀 Modo Visualizador (Somente Leitura):** Convidados podem navegar por todas as informações, tabelas, relatórios e fotos sem permissão de alteração.
- **💡 Caixa de Sugestões:** Qualquer convidado ou participante pode enviar sugestões e ideias diretamente pela interface.
- **📜 Log de Auditoria:** Todas as inclusões, edições de valores/quantidades e exclusões são registradas no histórico com autor, data/hora e detalhamento da alteração.

### 3. Motor de Cálculo e Arredondamento Comercial
- **Consumo Típico por Pessoa:** Cálculo dinâmico de bebidas, carnes e descartáveis baseado na contagem de participantes confirmados.
- **Arredondamento Automático para Embalagens Comerciais:**
  - Bebidas: Garrafas de 2L, 3L, 1,5L, latas ou fardos.
  - Descartáveis: Pacotes fechados de 50 ou 100 unidades.
  - Gelo e Carvão: Sacos de 5kg, 10kg ou 15kg.
- **Consumíveis Fabricados por Colaboradores (Receitas):**
  - Preparo de **Farofas**, **Vinagretes**, **Tortas**, etc.
  - Cada receita possui sua lista de ingredientes escalados proporcionalmente para a quantidade de pessoas.
  - Todos os ingredientes são consolidados na Lista de Compras Geral por fornecedor.

### 4. Atribuição de Tarefas
- Atribuição direta aos nomes dos colaboradores (ex: *quem faz a farofa: Manuela*, *quem compra o pão de alho: Marcelle*, *quem compra os picolés: Júlia*, *quem comanda a churrasqueira: Matusalém*).
- **Portal "Minhas Tarefas":** Visualização filtrada para cada colaborador atualizar status (`Pendente`, `Em Andamento / Parcial`, `Realizada`, `Cancelada`), registrar gastos reais e adicionar notas.

### 5. Controle de Caixa e Comprovantes Fiscais
- Gestão de Entradas (cotas pagas por alunos e servidores, patrocínios).
- Gestão de Saídas (compras efetuadas e reembolsos via PIX).
- **Upload de Cupons e Notas Fiscais:** Suporte para envio de fotos tiradas pelo celular ou arquivos PDF/JPG/PNG.
- **Galeria de Comprovantes:** Pré-visualização na tela e download de arquivos anexados.
- Apuração automática de sobras e saldo remanescente em caixa.

### 6. Relatórios Interativos e Emissão em PDF
- **Relatório Geral Executivo do Evento (PDF e Tela):** Resumo executivo com participantes, consumíveis, receitas e quadro de tarefas.
- **Prestação de Contas & Fluxo de Caixa (PDF e Tela):** Extrato completo de entradas, saídas, PIX e saldo.
- **Lista de Compras Consolidada (PDF e Tela):** Itens e ingredientes com volumes e quantidades de pacotes comerciais a adquirir.
- **Relatório de Tarefas e Colaboradores (PDF e Tela):** Checklist operacional com responsáveis e prazos.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- Python 3.10+ instalado no sistema.

### Passo a Passo
1. Ative o ambiente virtual (ou crie um novo caso necessário):
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. Instale as dependências:
   ```powershell
   pip install -r requirements.txt
   ```
3. Inicie o aplicativo Streamlit:
   ```powershell
   streamlit run app.py
   ```
4. Abra o navegador no endereço indicado (geralmente `http://localhost:8501`).

---

## 🔐 Credenciais Iniciais de Demonstração

| Usuário | Senha | Perfil | Descrição |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | 👑 Master | Administrador principal do sistema |
| `matusalem` | `matu123` | 👑 Master | Mestre Churrasqueiro e Organizador |
| `manuela` | `manu123` | 🛠️ Colaborador | Responsável pelo Vinagrete e Farofa |
| `marcelle` | `marcelle123` | 🛠️ Colaborador | Responsável pela Compra do Pão de Alho |
| `julia` | `julia123` | 🛠️ Colaborador | Responsável pelos Picolés e Sobremesas |
| `convidado` | `1234` | 👀 Visualizador | Acesso público em modo somente leitura |

*(Novos usuários e administradores podem ser cadastrados na aba Administração & Auditoria).*

---

## 📁 Estrutura de Diretórios
```
Calculadora_Churrasco/
├── app.py                      # Aplicação Streamlit principal
├── config.py                   # Configurações de pastas e caminhos
├── requirements.txt            # Dependências Python
├── README.md                   # Documentação do projeto
├── Gastos com churrasco...xlsx # Planilha histórica original
├── services/
│   ├── auth_service.py         # Autenticação, permissões e senhas
│   ├── event_service.py        # Gestão de eventos, pastas e clonagem isolada
│   ├── calculation_service.py  # Motor de cálculo de porções, embalagens e receitas
│   ├── excel_importer.py       # Importador da planilha demonstrativa 3º ELE 2025
│   ├── pdf_service.py          # Gerador de relatórios em PDF com FPDF2
│   └── storage_service.py      # Persistência JSON e trilha de auditoria
├── ui/
│   ├── auth_view.py            # Barra de identificação e login
│   ├── event_selector.py       # Seletor, criador e clonador de eventos
│   ├── dashboard_view.py       # Painel executivo com métricas e gráficos
│   ├── participants_view.py    # Gestão de consumidores e colaboradores
│   ├── consumables_view.py     # Carnes, bebidas, embalagens e receitas fabricadas
│   ├── tasks_view.py           # Portal "Minhas Tarefas" e quadro geral
│   ├── cashflow_view.py        # Controle de caixa e upload de comprovantes
│   ├── suppliers_view.py       # Fornecedores, preços e fotos de cotação
│   ├── reports_view.py         # Relatórios na tela e exportação para PDF
│   ├── suggestions_view.py     # Mural de sugestões da turma
│   └── admin_view.py           # Administração de contas e logs de auditoria
└── data/
    ├── global/users.json       # Usuários do sistema
    └── events/{event_id}/      # Pasta isolada de cada evento
        ├── meta.json
        ├── participants.json
        ├── collaborators.json
        ├── consumables.json
        ├── recipes.json
        ├── tasks.json
        ├── cashflow.json
        ├── suggestions.json
        ├── audit_log.json
        └── uploads/
            ├── receipts/       # Cupons fiscais e comprovantes PIX
            └── suppliers/      # Fotos de preços e tabelas de fornecedores
```

