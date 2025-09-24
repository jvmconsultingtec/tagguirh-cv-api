# 🚀 CV Parser API - Sistema Simplificado

Sistema avançado para processamento de currículos em PDF **APENAS via URLs**.

## ✨ Funcionalidades

### 🔥 **Parser Avançado (Enhanced)**
- ✅ **IA/ML**: Extração inteligente com spaCy
- ✅ **Experiências**: Empresas, cargos, datas, tech stack
- ✅ **Educação**: Instituições, cursos, certificações
- ✅ **Skills**: Níveis de proficiência (expert, advanced, etc.)
- ✅ **Projetos**: Detalhamento completo de projetos
- ✅ **Achievements**: Conquistas e realizações
- ✅ **Localização**: Cidade, estado, país (limpeza automática)
- ✅ **Summary**: Resumo profissional automático
- ✅ **Filtros**: Remove empresas/instituições inválidas

### 🌐 **Suporte a URLs**
- ✅ **Google Drive**: Conversão automática de URLs
- ✅ **URLs Diretas**: Qualquer PDF via URL
- ✅ **Validação**: Verificação de content-type
- ✅ **Download**: Processamento temporário
- ✅ **Limpeza**: Remove arquivos temporários automaticamente

## 🏗️ Arquitetura

```
📦 Sistema
├── 📄 main.py              # API principal + endpoint único
├── 🧠 enhanced_parser.py   # Parser avançado com IA/ML
├── 📋 requirements.txt     # Dependências
└── 📖 README.md           # Documentação
```

### 🔧 **Componentes:**

**main.py:**
- FastAPI application
- Endpoint único para URLs
- Download e validação de PDFs
- Integração com enhanced_parser

**enhanced_parser.py:**
- Parser avançado com spaCy
- Extração de experiências complexas
- Análise de skills e níveis
- Detecção de projetos e achievements
- Processamento de localização
- Filtros de qualidade

## 🚀 Instalação

### 1. Dependências
```bash
pip3 install -r requirements.txt
```

### 2. spaCy (Opcional - para parser avançado)
```bash
python3 -m spacy download pt_core_news_lg
```

### 3. Executar API
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 Endpoints

### 🌐 **URLs (Único Endpoint)**

| Método | Endpoint | Descrição | Parser |
|--------|----------|-----------|---------|
| POST | `/cv:parse-single-url-enhanced` | Parse único PDF de URL | **Avançado** |
| GET | `/health` | Health check | - |

## 🔗 URLs Suportadas

- ✅ **Google Drive**: `https://drive.google.com/file/d/FILE_ID/view`
- ✅ **Google Drive Direto**: `https://drive.google.com/uc?export=download&id=FILE_ID`
- ✅ **URLs Diretas**: Qualquer URL que retorne PDF
- ✅ **Validação**: Content-type e assinatura PDF

## 📝 Exemplos de Uso

### 🌐 **Parse Avançado de URL (ÚNICO ENDPOINT)**
```bash
curl -X POST "http://localhost:8000/cv:parse-single-url-enhanced" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://drive.google.com/file/d/1aw4CS3xgPws-zzNHBrw1-35eHRA6WIaD/view"}'
```

### 🌐 **Parse com URL Direta**
```bash
curl -X POST "http://localhost:8000/cv:parse-single-url-enhanced" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://exemplo.com/curriculo.pdf"}'
```

### 🔍 **Health Check**
```bash
curl http://localhost:8000/health
```

## 📊 Exemplo de Resposta (Parser Avançado)

```json
{
  "file": "curriculo.pdf",
  "hash": "abc123...",
  "data": {
    "candidate": {
      "full_name": "João Vitor Miguel",
      "emails": ["joao@email.com"],
      "phones": ["+5511999999999"],
      "location": {
        "city": "Blumenau",
        "state": "Santa Catarina",
        "country": "Brasil"
      },
      "links": {
        "linkedin": "https://linkedin.com/in/joaosilva",
        "github": "https://github.com/joaosilva"
      }
    },
    "summary": "Sou apaixonado por liderar equipes...",
    "skills": [
      {
        "name": "Java",
        "level": "expert",
        "confidence": 0.9
      },
      {
        "name": "JavaScript",
        "level": "advanced",
        "confidence": 0.8
      }
    ],
    "languages": [
      {
        "name": "Portuguese",
        "level_cefr": "C1",
        "confidence": 0.9
      }
    ],
    "experiences": [
      {
        "company": "Empresa ABC",
        "role": "Desenvolvedor Senior",
        "start_date": "2020-01",
        "end_date": null,
        "is_current": true,
        "tech_stack": ["Java", "Spring", "AWS"],
        "confidence": 1.0
      }
    ],
    "education": [
      {
        "institution": "Universidade XYZ",
        "degree": "Bacharelado em Ciência da Computação",
        "start_date": "2015-01",
        "end_date": "2019-12",
        "confidence": 0.8
      }
    ],
    "meta": {
      "projects": [
        {
          "name": "Sistema de Vendas",
          "description": "Sistema completo de gestão de vendas",
          "technologies": ["Java", "Spring", "MySQL"],
          "confidence": 0.8
        }
      ],
      "achievements": [
        "Liderou equipe de 10 desenvolvedores",
        "Implementou arquitetura de microserviços"
      ],
      "parser_version": "enhanced"
    }
  },
  "confidence_overall": 0.95,
  "processing_ms": 2500
}
```

## 🛠️ Dependências

```txt
fastapi==0.117.1          # Framework web
uvicorn[standard]==0.37.0  # Servidor ASGI
python-dotenv==1.1.1      # Variáveis de ambiente
pydantic==2.11.9          # Validação de dados
pymupdf==1.26.4           # Processamento de PDF
spacy==3.8.7              # NLP (opcional)
requests==2.32.4          # HTTP requests
aiohttp==3.12.15          # HTTP assíncrono
```

## ⚡ Performance

### **Parser Avançado:**
- ⚡ **Velocidade**: ~2-3s por PDF
- 🎯 **Precisão**: 90-95%
- 💾 **Memória**: Média (spaCy)
- 🧹 **Limpeza**: Filtros automáticos de qualidade

## 🔧 Configuração

### **spaCy (Opcional)**
```bash
# Instalar modelo português
python3 -m spacy download pt_core_news_lg

# Verificar instalação
python3 -c "import spacy; nlp = spacy.load('pt_core_news_lg'); print('OK')"
```

## 🚨 Troubleshooting

### **Erro: "Parser melhorado não disponível"**
```bash
pip3 install spacy
python3 -m spacy download pt_core_news_lg
```

### **Erro: "URL não aponta para um arquivo PDF"**
- Verifique se a URL é válida
- Para Google Drive, use: `https://drive.google.com/uc?export=download&id=FILE_ID`

## 📈 Melhorias Implementadas

- ✅ **Filtros de Qualidade**: Remove empresas/instituições inválidas
- ✅ **Limpeza de Dados**: Remove "IA" de nomes de cidades
- ✅ **Extração de Nome**: Prioriza email para maior precisão
- ✅ **Validação**: Filtra experiências e educação com dados null
- ✅ **Simplificação**: Apenas 1 endpoint para máxima simplicidade

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---

**Versão**: 2.0.0  
**Autor**: Sistema CV Parser Simplificado  
**Última Atualização**: 2024-09-23
