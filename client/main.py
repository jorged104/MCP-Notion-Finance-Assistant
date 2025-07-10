from textual.app import App, ComposeResult
from textual.containers import Container
from textual.containers import VerticalScroll
from textual.widgets import Markdown, Static
from textual.widgets import Header, Footer, Input, Static, RichLog
from config import load_config
from utils import printGraph
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from graph_builder import build_graph # <-- Importar la nueva función
import asyncio
import uuid
from pathlib import Path

class FinanceAssistantApp(App):
    CSS_PATH = "main.tcss"
    BINDINGS = [("q", "quit", "Salir")]

    def __init__(self):
        super().__init__()
        self.graph = None
        self.config_graph = None
        self.total_tokens_used = 0
        self.thread_id = str(uuid.uuid4())
        self.chat_log = None
        self.query_input = None
        self.graph_ready = False
        self.client_manager = None
        self.last_ai = None

    def compose(self) -> ComposeResult:
        """Compone la interfaz de usuario"""
        yield Header()
        with Container():
            self.message_area = VerticalScroll(id="chat_area")
            self.query_input = Input(placeholder="Inicializando... Por favor espera...")
            # Deshabilitar input hasta que esté listo
            self.query_input.disabled = False
            yield self.message_area
            yield self.query_input
        yield Footer()

    async def on_mount(self) -> None:
        """Se ejecuta después de que la interfaz esté montada"""
        # Ahora los widgets ya existen
        self.message_area.mount(
    Static("🔧 Inicializando Finance Assistant..."))
        
        # Usar un worker para setup asíncrono no bloqueante
        self.run_worker(self.setup_graph(), exclusive=True, name="setup")

    async def setup_graph(self):
        """Configura el grafo de manera asíncrona"""
        try:
            self.message_area.mount(  Static("📦 Cargando configuración..."))
            config = load_config()

            self.message_area.mount(Static("🔧 Conectando al MCP..."))
            
            # Configurar MCP client
            current_dir = Path(__file__).parent
            finance_js = current_dir.parent / "servers" / "finance" / "build" / "finance.js"

            self.client_manager = await MultiServerMCPClient({
                "finance": {
                    "command": "node",
                    "args": [str(finance_js)],
                    "transport": "stdio",
                    "env": {
                        "NOTION_TOKEN": config["notion"]["api_key"],
                        "NOTION_DB_ACCOUNTS": config["notion"]["db_accounts"],
                        "NOTION_DB_TRANSACTIONS": config["notion"]["db_transactions"]
                    }
                }
            }).__aenter__()

            self.message_area.mount(Static("🛠️ Obteniendo herramientas y recursos..."))
            tools = self.client_manager.get_tools()
            resources = await self.client_manager.get_resources(server_name="finance")
            resource_names = [r.as_string() for r in resources]

            self.message_area.mount(Static("📊 Construyendo grafo de estados..."))
            self.graph = build_graph(config, tools, resource_names)
            self.config_graph = {"configurable": {"thread_id": self.thread_id}}
            
            # Imprimir grafo (si la función existe)
            try:
                printGraph(self.graph)
            except Exception as e:
                self.message_area.mount(Static(f"⚠️ No se pudo imprimir el grafo: {e}"))

            # Marcar como listo
            self.graph_ready = True
            
            # Habilitar input y actualizar placeholder
            self.query_input.disabled = False
            self.query_input.placeholder = "Escribe tu pregunta y presiona Enter..."
            
            self.message_area.mount(Static("✅ Finance Assistant iniciado correctamente. Escribe tu pregunta."))
            self.query_input.focus()

        except Exception as e:
            self.message_area.mount(Static(f"❌ Error durante la inicialización: {str(e)}"))
            self.message_area.mount(Static("Revisa la configuración y las dependencias."))
            # Mantener input deshabilitado en caso de error
            self.query_input.placeholder = "Error en inicialización - App no disponible"

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        """Maneja el envío de mensajes"""
        if not self.graph_ready:
            self.message_area.mount(Static("⚠️ El sistema aún se está inicializando. Por favor espera."))
            return

        text = message.value.strip()
        if not text:
            return
            
        self.query_input.value = ""
        
        if text.lower() in {"exit", "quit", "q"}:
            self.action_quit()
            return

        self.message_area.mount(Static(f"> {text}"))
        
        # Deshabilitar input mientras procesa
        self.query_input.disabled = True
        self.query_input.placeholder = "Procesando..."
        
        try:
            response_received = False
            self.last_ai = None
            async for event in self.graph.astream(
                {"messages": [HumanMessage(content=text)]},
                self.config_graph,
                stream_mode="values"
            ):
                if "messages" in event and event["messages"]:
                    last = event["messages"][-1]
                    if getattr(last, "type", "") == "ai":
                        self.last_ai = last.content
            if self.last_ai:
                self.message_area.mount(Markdown(self.last_ai + "\n\n" , classes="ai-msg"))
        except Exception as outer_error:
            import traceback
            trace = traceback.format_exc()
            self.message_area.mount(Static(f"❌ Error externo al procesar el stream:\n{trace}")    )
        finally:
            # Rehabilitar input
            self.query_input.disabled = False
            self.query_input.placeholder = "Escribe tu pregunta y presiona Enter..."
            self.query_input.focus()

    def action_quit(self):
        """Acción para salir de la aplicación"""
        self.message_area.mount(Static(f"👋 Cerrando sesión. Tokens usados: {int(self.total_tokens_used)}"))
        self.exit()

async def main():
    """Función principal asíncrona para ejecutar la app."""
    app = FinanceAssistantApp()
    await app.run_async()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error ejecutando la aplicación: {e}")
        import traceback
        traceback.print_exc()
