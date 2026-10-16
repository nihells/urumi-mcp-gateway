\# Urumi MCP Gateway — System Design



\## 1. Overview



Urumi MCP Gateway provides a centralized interface for accessing multiple

Model Context Protocol (MCP) servers through authenticated REST and MCP

endpoints.



The system includes a FastAPI backend, a React frontend, upstream MCP

servers, and a WooCommerce integration.



\## 2. Architecture



```mermaid

flowchart TD

&#x20;   User\[User / MCP Client]

&#x20;   UI\[React Frontend]

&#x20;   API\[FastAPI Backend]

&#x20;   Auth\[Authentication and Authorization]

&#x20;   Gateway\[MCP Gateway]

&#x20;   Unified\[Unified MCP Endpoint]

&#x20;   Woo\[WooCommerce MCP Server]

&#x20;   Utility\[Utility MCP Server]

&#x20;   Text\[Text Tools MCP Server]

&#x20;   Store\[(SQLite Database)]

&#x20;   Shop\[WordPress / WooCommerce]



&#x20;   User --> UI

&#x20;   UI --> API

&#x20;   API --> Auth

&#x20;   Auth --> Gateway

&#x20;   Auth --> Unified

&#x20;   API --> Store

&#x20;   Gateway --> Woo

&#x20;   Unified --> Woo

&#x20;   Gateway --> Utility

&#x20;   Unified --> Utility

&#x20;   Gateway --> Text

&#x20;   Unified --> Text

&#x20;   Woo --> Shop
