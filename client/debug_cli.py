

import asyncio
import uuid
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from config import load_config
from graph_builder import build_graph
from utils import printGraph

async def main():
    """
    Función principal para ejecutar el agente en modo de depuración de consola.
    """
    print("🔧 Inicializando Finance Assistant en modo DEBUG...")
    
    thread_id = str(uuid.uuid4())
    
    try:
        print("📦 Cargando configuración...")
        config = load_config()

        print("🔧 Conectando al MCP...")
        client = await MultiServerMCPClient({
            "finance": {
                "command": "node",
                "args": ["C:/Users/jdmonterroson/Documents/tempproyect/mcp-finance-asistant/servers/finance/build/finance.js"],
                "transport": "stdio",
                "env": {
                    "NOTION_TOKEN": config["notion"]["api_key"],
                    "NOTION_DB_ACCOUNTS": config["notion"]["db_accounts"],
                    "NOTION_DB_TRANSACTIONS": config["notion"]["db_transactions"]
                }
            }
        }).__aenter__()

        print("🛠️ Obteniendo herramientas y recursos...")
        tools = client.get_tools()
        resources = await client.get_resources(server_name="finance")
        resource_names = [r.as_string() for r in resources]

        print("📊 Construyendo grafo de estados...")
        graph = build_graph(config, tools, resource_names)
        config_graph = {"configurable": {"thread_id": thread_id}}

        try:
            print("📈 Visualización del grafo:")
            printGraph(graph)
        except Exception as e:
            print(f"⚠️ No se pudo imprimir el grafo: {e}")

        print("\n✅ Finance Assistant iniciado. Escribe tu consulta o 'salir' para terminar.")
        
        while True:
            print("\n> ", end="")
            text = await asyncio.to_thread(input) # Usar input no bloqueante
            
            if text.lower() in {"salir", "exit", "quit", "q"}:
                print("👋 Cerrando sesión.")
                break
            
            if not text.strip():
                continue

            print("🔄 Procesando...")
            
            try:
                async for event in graph.astream(
                    {"messages": [HumanMessage(content=text)]},
                    config_graph,
                    stream_mode="values"
                ):
                    print("--- DEBUG EVENT ---")
                    print(event)
                    print("-------------------")
                    
                    if "messages" in event and event["messages"]:
                        last = event["messages"][-1]
                        if hasattr(last, 'content') and last.content and hasattr(last, 'type'):
                            if last.type == "ai":
                                print(f"🤖 Asistente: {last.content}")

            except Exception as e:
                print(f"❌ Error procesando consulta: {str(e)}")
            print("🔄 Consulta procesada........................................")

    except Exception as e:
        print(f"❌ Error fatal durante la inicialización: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Interrupción por teclado. Adiós.")

