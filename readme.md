# 🎭 Perfume Advisor Sales Bot

> **AI-Powered Perfume Recommendation System with Multi-Modal Journaling**

A Flask-based backend service that leverages AI to provide personalized perfume recommendations through intelligent conversation, contextual understanding, and seamless e-commerce integration. This system serves as the core recommendation engine for a perfume brand, offering both product-specific guidance and life journaling capabilities.

## 🎯 Project Overview

This project addresses the complex challenge of matching users with their ideal perfumes through intelligent AI-driven conversations. Unlike traditional recommendation systems, this platform combines:

- **Semantic Search**: Vector-based perfume discovery using Pinecone
- **Conversational AI**: Context-aware recommendations through natural language processing
- **Multi-Modal Journaling**: Product tracking and life reflection features
- **E-commerce Integration**: Real-time Shopify product registration
- **Intent Recognition**: Smart conversation flow management

The system processes user preferences, conversation history, and contextual factors (weather, occasion, mood) to deliver highly personalized fragrance recommendations.

## ✨ Key Features

### 🧠 **Intelligent Recommendation Engine**

- **Vector-based Search**: Leverages Pinecone for semantic perfume discovery across internal and external databases
- **Context-Aware Matching**: Considers user goals, preferences, weather, and conversation history
- **Dynamic Filtering**: Excludes disliked perfumes and adapts to user selections in real-time
- **Multi-Goal Distribution**: Intelligently groups recommendations by user objectives (confidence, uniqueness, mood, attraction)

### 💬 **Conversational AI Interface**

- **Intent Recognition**: Automatically detects whether users need recommendations or casual conversation
- **Conversation Continuity**: Maintains context across multiple interactions
- **Personalized Responses**: Adapts tone and recommendations based on user profile and history
- **Multi-Platform Support**: Handles landing page, home page, and dashboard conversations

### 📝 **Advanced Journaling System**

- **Product Journal**: Track perfume experiences with AI-powered insights and recommendations
- **Life Journal**: Multi-mode reflection system (Work, Health, Relationship, General)
- **Smart Summaries**: AI-generated conversation summaries and insights
- **Contextual Recommendations**: Seamless transition from journaling to product suggestions

### 🛒 **E-commerce Integration**

- **Real-time Shopify Sync**: Automatically registers external perfumes with metafields
- **Retry Logic**: Robust error handling with exponential backoff
- **Inventory Management**: Handles product variants and availability
- **Collection Organization**: Intelligent product categorization

### 🔧 **Technical Excellence**

- **Microservice Architecture**: Designed as part of a larger distributed system
- **CORS Management**: Secure cross-origin resource sharing
- **Error Handling**: Comprehensive exception management with detailed logging
- **Background Processing**: Asynchronous tasks for non-blocking operations

## 🛠 Tech Stack & Skills Demonstrated

### **Backend Framework**

- **Flask 3.1.0**: Modern Python web framework with blueprint architecture
- **Gunicorn**: Production-grade WSGI server for deployment

### **AI & Machine Learning**

- **OpenAI GPT Models**: Advanced language model integration for natural conversations
- **Groq API**: High-performance LLM inference for real-time responses
- **Pinecone**: Vector database for semantic search and similarity matching

### **Database & Storage**

- **MongoDB**: NoSQL database for flexible data modeling
- **PyMongo**: Python driver for MongoDB operations
- **ObjectId Management**: Efficient document identification and querying

### **E-commerce & APIs**

- **Shopify GraphQL API**: Advanced e-commerce integration
- **RESTful API Design**: Clean, consistent endpoint architecture
- **GraphQL Mutations**: Complex product creation and management

### **DevOps & Deployment**

- **Environment Management**: Secure configuration with python-dotenv
- **CORS Configuration**: Cross-origin resource sharing for frontend integration
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging for debugging and monitoring

### **Data Processing**

- **JSON Handling**: Complex data serialization and parsing
- **Vector Embeddings**: Multilingual text embedding for semantic search
- **Context Management**: Intelligent conversation state tracking

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8+
- MongoDB instance
- Pinecone account and API key
- OpenAI/Groq API key
- Shopify store credentials

### Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/MH-PAVEL/perfume-advisor-sales-bot
   cd perfume-advisor-sales-bot
   ```

2. **Set up virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file with:

   ```env
   MONGO_URI=your_mongodb_connection_string
   PINECONE_API=your_pinecone_api_key
   GROK_API_KEY=your_grok_api_key
   GROK_ENDPOINT=your_grok_endpoint
   SHOPIFY_STORE_URL=your_shopify_graphql_endpoint
   SHOPIFY_ACCESS_TOKEN=your_shopify_access_token
   CORS_ORIGIN=your_frontend_url
   LLM_GROQ_API_KEY=
   LLM_SECONDARY_GROQ_API_KEY=
   ```

5. **Run the development server**
   ```bash
   python run.py
   ```

The server will start on `http://localhost:5500`

## 🏗 Architecture Overview

### **System Components**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend Application                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ Landing     │ │ Home        │ │ Dashboard   │ │ Journal     │ │
│  │ Page        │ │ Page        │ │ Interface   │ │ System      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend API Service                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ Landing     │ │ Home        │ │ Dashboard   │ │ Journal     │ │
│  │ Routes      │ │ Routes      │ │ Routes      │ │ Routes      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI & External Services                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
│  │ OpenAI      │ │ Groq API    │ │ Pinecone    │ │ Shopify     │ │
│  │ (GPT Models)│ │ (LLM)       │ │ (Vector DB) │ │ (E-commerce)│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ MongoDB (Conversations, Journals, User Data)               │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### **Service Communication Flow**

```
Next.js Frontend
    │
    ├── Landing Page Features
    │   ├── Initial perfume recommendations
    │   ├── User preference collection
    │   └── Conversation initiation
    │
    ├── Home Page Features
    │   ├── Extended conversations
    │   ├── Recommendation refinement
    │   └── Context-aware responses
    │
    ├── Dashboard Features
    │   ├── User-specific conversations
    │   ├── Persistent chat history
    │   └── Personalized recommendations
    │
    └── Journal Features
        ├── Product experience tracking
        ├── Life reflection sessions
        └── AI-powered insights

Flask Backend API
    │
    ├── Request Processing
    │   ├── Input validation
    │   ├── User intent detection
    │   └── Context management
    │
    ├── AI Integration
    │   ├── LLM conversation handling
    │   ├── Vector search coordination
    │   └── Recommendation generation
    │
    ├── Data Management
    │   ├── MongoDB operations
    │   ├── Conversation persistence
    │   └── Journal data handling
    │
    └── E-commerce Sync
        ├── Shopify product registration
        ├── Inventory management
        └── Background processing
```

### **Key Design Patterns**

- **Factory Pattern**: App creation with `create_app()` function
- **Repository Pattern**: Database operations abstracted through utility modules
- **Strategy Pattern**: Different recommendation strategies based on user goals
- **Observer Pattern**: Background processing for non-blocking operations

### **Data Flow**

1. **User Input** → Intent Recognition → Context Retrieval
2. **Vector Search** → Semantic Matching → Perfume Filtering
3. **AI Analysis** → Recommendation Generation → Response Formatting
4. **Database Storage** → Conversation Persistence → E-commerce Sync

## 🎯 Challenges & Solutions

### **Challenge 1: Semantic Search Optimization**

**Problem**: Balancing internal vs external perfume recommendations while maintaining relevance.

**Solution**: Implemented intelligent ratio-based distribution (75% internal, 25% external) with goal-based grouping and dynamic filtering based on user preferences.

### **Challenge 2: Conversation Context Management**

**Problem**: Maintaining coherent conversations across multiple interactions while managing token limits.

**Solution**: Developed conversation history truncation (last 6 exchanges) and intelligent context extraction to balance memory usage with conversation quality.

### **Challenge 3: E-commerce Integration Reliability**

**Problem**: Handling Shopify API failures and ensuring product registration consistency.

**Solution**: Implemented retry logic with exponential backoff, comprehensive error handling, and background processing for non-critical operations.

### **Challenge 4: Multi-Modal Intent Recognition**

**Problem**: Distinguishing between recommendation requests and casual conversation.

**Solution**: Built intelligent intent detection using LLM analysis of user prompts, conversation history, and contextual clues.

## 🔒 Security & Performance

### **Security Features**

- **CORS Protection**: Configured cross-origin resource sharing
- **Input Validation**: Comprehensive request validation and sanitization
- **Error Handling**: Secure error responses without sensitive information exposure
- **Environment Variables**: Secure configuration management

### **Performance Optimizations**

- **Vector Search**: Efficient semantic matching with Pinecone
- **Background Processing**: Non-blocking operations for better user experience
- **Connection Pooling**: Optimized database connections
- **Response Caching**: Intelligent caching of frequently accessed data

## 📝 Development Notes

### **MVP Considerations**

This project was developed as an **MVP (Minimum Viable Product)** to deliver rapid functionality. As such, some areas would benefit from refactoring in a production environment:

- **Code Organization**: Some utility functions could be better modularized
- **Error Handling**: More granular exception handling could be implemented
- **Testing**: Comprehensive test coverage would enhance reliability
- **Documentation**: Inline documentation could be more extensive

### **Microservice Architecture**

This backend is designed as part of a larger microservice architecture where:

- **Authentication** is handled by a dedicated auth service
- **User Management** is managed by a separate user service
- **This service** focuses purely on recommendation logic and conversation management

## 🎉 Call to Action

Ready to experience intelligent perfume recommendations?

- ⭐ **Star this repository** if you found it helpful
- 🔄 **Fork it** to create your own version
- 💬 **Open an issue** for bugs or feature requests
- 🤝 **Submit a PR** to contribute improvements

This project demonstrates advanced AI integration, e-commerce automation, and conversational UX design. Perfect for showcasing skills in modern web development, AI/ML integration, and scalable backend architecture.

---

**Built with ❤️ using Flask, OpenAI, Pinecone, and MongoDB**
