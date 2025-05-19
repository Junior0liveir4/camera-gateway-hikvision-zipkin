# 📷 Camera Hikvision Gateway

Gateway de integração com câmera Hikvision, adaptado para realizar **exportação de dados para o Zipkin**, permitindo **tracing distribuído** das capturas e envios de imagem. Esta aplicação foi adaptada para compatibilidade com o restante do ecossistema do **LabSEA**, garantindo uniformidade com as outras câmeras já instrumentadas.

## 🛠 Funcionalidade

A aplicação tem como principal objetivo:

- Conectar-se a uma **câmera IP da marca Hikvision**.
- Capturar imagens por meio do protocolo **RTSP**.
- Publicar os quadros capturados no tópico RabbitMQ:  
  `CameraGateway.5.Frame`
- Exportar dados de tracing para o **Zipkin**, facilitando a análise de desempenho e rastreabilidade.

## 📦 Arquitetura

- **Linguagem:** Python
- **Publicação:** RabbitMQ (AMQP)
- **Tracing:** OpenCensus + Zipkin
- **Execução:** Kubernetes (1 pod)
- **Imagem Docker:** construída via `Dockerfile`

---

## 📁 Estrutura dos Arquivos

| Arquivo | Descrição |
|--------|-----------|
| `Dockerfile` | Define a imagem Docker da aplicação |
| `deployment.yaml` | Define o `Deployment` e o `ConfigMap` do Kubernetes |
| `config.json` | Parâmetros de configuração da câmera, broker e Zipkin |
| `gateway.py` | Código principal que inicializa a aplicação |
| `hikvision.py` | Interface com a câmera Hikvision via RTSP |
| `service.py` | Serviço que realiza a captura das imagens e envio para o broker |
| `requirements.txt` | Dependências da aplicação Python |

---

## 🧠 Explicação dos Componentes

### `service.py`
Contém a lógica central do gateway. Ele:

1. Conecta-se à câmera IP Hikvision usando o `hikvision.py`.
2. Captura imagens de forma contínua.
3. Publica os quadros no tópico RabbitMQ especificado.
4. Adiciona *tracing spans* com a biblioteca OpenCensus para exportação ao Zipkin.

### `hikvision.py`
Implementa o acesso à câmera usando:

- RTSP para captura de vídeo.
- OpenCV para extração de quadros.
- Conversão e compressão da imagem no formato definido (`JPEG`).

---

## 📦 Dependências

Instaladas automaticamente via `requirements.txt`:

```
six==1.16.0
is-wire==1.2.1
is-msgs==1.1.18
protobuf==3.20.3
opencensus==0.5.0
opencensus-ext-zipkin==0.2.1
vine==5.1.0
opencv-python
numpy
xmltodict
```

---

## ☁️ Execução no Kubernetes

### 1. Pré-requisitos

- Cluster Kubernetes ativo
- Acesso ao RabbitMQ e Zipkin
- `kubectl` configurado

### 2. Aplicação do Deployment

Use o arquivo `deployment.yaml`:

```bash
kubectl apply -f deployment.yaml
```

Esse arquivo define:

- Um `Deployment` com **1 réplica**
- Um `ConfigMap` contendo:
  - IP e porta do broker (RabbitMQ)
  - URL do Zipkin
  - Configurações da câmera

**Recursos definidos:**

```yaml
resources:
  requests:
    cpu: "1"
    memory: 512Mi
```

Esses valores funcionam corretamente, mas podem ser ajustados conforme a carga.

---

## 🌐 Testes e Validação

1. Acesse a aplicação via browser apontando para o IP/porta do serviço no cluster.
2. Verifique a publicação no tópico RabbitMQ: `CameraGateway.5.Frame`.
3. Acesse a interface do **Zipkin** e valide os *traces* gerados.

---

## 🔧 Variáveis de Ambiente

As variáveis são carregadas do `ConfigMap` embutido no `deployment.yaml`. Exemplo de conteúdo:

```yaml
data:
  config.json: |
    {
      "broker_uri": "amqp://rabbitmq:30000",
      "zipkin_url": "http://zipkin:30200",
      ...
    }
```

---

## 📈 Observabilidade com Zipkin

A instrumentação com `opencensus-ext-zipkin` permite rastrear:

- Total de tempo da operação

Essa informação é enviada automaticamente ao Zipkin.

---

## 📌 Notas Adicionais

- A modificação foi feita para equiparar esta câmera Hikvision com os outros modelos usados no **LabSEA**.
- Apenas **um pod** é necessário para executar esta aplicação.
- A câmera utiliza o padrão de compressão **H.264**, com resolução **1920x1080 a 60fps**.
- As imagens são enviadas no formato **JPEG** com compressão de **0.8**.

---

## 📬 Contato

Para dúvidas ou sugestões, entre em contato com o time do **LabSEA**.
