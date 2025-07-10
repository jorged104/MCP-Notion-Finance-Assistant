from typing import Dict, Any
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage


def make_finance_qa_node(llm: BaseLanguageModel, finance_catalog_json: list[str]):
    catalogs_block = "\n".join(finance_catalog_json)
    today = datetime.today().strftime("%Y-%m-%d")

    system_prompt = f"""
Eres Finance-Expert-QA, un asistente especializado en responder preguntas financieras del usuario usando las herramientas disponibles.
Catálogos disponibles:
{catalogs_block}
Puedes responder cosas como:
- ¿Cuánto gasté este mes en transporte?
- ¿Cuál fue el gasto más alto en marzo?
- ¿Qué suscripciones tengo?
- ¿Cuál es el saldo de mi cuenta?
Siempre usa herramientas para responder. No inventes datos. Si necesitas más información, pídesela al usuario.
Responde siempre en formato markdown
Fecha actual: {today}
"""

    def clean_and_optimize_messages(messages: list, max_messages: int = 12) -> list:
        """
        Limpia y optimiza la lista de mensajes manteniendo el contexto importante
        """
        if not messages:
            return [SystemMessage(content=system_prompt)]
        
        # Paso 1: Tomar los mensajes más recientes
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        # Paso 2: Identificar y marcar secuencias válidas de tool_calls
        valid_sequences = []
        i = 0
        
        while i < len(recent_messages):
            msg = recent_messages[i]
            
            if isinstance(msg, (HumanMessage, SystemMessage)):
                # Mensajes del usuario y sistema siempre son válidos
                valid_sequences.append((i, msg, True))
                i += 1
                
            elif isinstance(msg, AIMessage):
                # Si tiene tool_calls, buscar los ToolMessages correspondientes
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_call_ids = [tc.get('id') for tc in msg.tool_calls if isinstance(tc, dict) and 'id' in tc]
                    
                    # Buscar ToolMessages correspondientes
                    tool_messages = []
                    j = i + 1
                    while j < len(recent_messages) and isinstance(recent_messages[j], ToolMessage):
                        tool_msg = recent_messages[j]
                        # Verificar si el ToolMessage corresponde a algún tool_call
                        if hasattr(tool_msg, 'tool_call_id') and tool_msg.tool_call_id in tool_call_ids:
                            tool_messages.append((j, tool_msg, True))
                        else:
                            # ToolMessage sin correspondencia, pero lo mantenemos por contexto
                            tool_messages.append((j, tool_msg, False))
                        j += 1
                    
                    # Si tenemos tool_calls, incluir la secuencia completa
                    if tool_messages:
                        valid_sequences.append((i, msg, True))
                        valid_sequences.extend(tool_messages)
                        i = j
                    else:
                        # AIMessage con tool_calls pero sin respuestas, mantener por contexto
                        valid_sequences.append((i, msg, False))
                        i += 1
                else:
                    # AIMessage normal sin tool_calls
                    valid_sequences.append((i, msg, True))
                    i += 1
                    
            elif isinstance(msg, ToolMessage):
                # ToolMessage huérfano, evaluar si mantenerlo por contexto
                # Si el mensaje anterior no es AIMessage con tool_calls, es huérfano
                if i > 0 and isinstance(recent_messages[i-1], AIMessage):
                    prev_msg = recent_messages[i-1]
                    if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                        # Ya debería haber sido procesado en el bloque anterior
                        pass
                    else:
                        # ToolMessage después de AIMessage sin tool_calls
                        valid_sequences.append((i, msg, False))
                else:
                    # ToolMessage completamente huérfano
                    valid_sequences.append((i, msg, False))
                i += 1
            else:
                # Otros tipos de mensaje
                valid_sequences.append((i, msg, True))
                i += 1
        
        # Paso 3: Filtrar mensajes priorizando los válidos y el contexto reciente
        filtered_messages = [SystemMessage(content=system_prompt)]
        
        # Separar mensajes válidos e inválidos
        valid_msgs = [seq for seq in valid_sequences if seq[2]]
        invalid_msgs = [seq for seq in valid_sequences if not seq[2]]
        
        # Incluir todos los mensajes válidos
        for _, msg, _ in valid_msgs:
            filtered_messages.append(msg)
        
        # Si tenemos espacio, incluir algunos mensajes inválidos para contexto
        remaining_space = max_messages - len(filtered_messages)
        if remaining_space > 0 and invalid_msgs:
            # Tomar los más recientes
            for _, msg, _ in invalid_msgs[-remaining_space:]:
                # Solo incluir si no rompe la secuencia
                if not isinstance(msg, ToolMessage) or len(filtered_messages) == 0 or not isinstance(filtered_messages[-1], ToolMessage):
                    filtered_messages.append(msg)
        
        return filtered_messages
    
    def compress_long_content(content: str, max_length: int = 800) -> str:
        """Comprime contenido muy largo manteniendo información clave"""
        if len(content) <= max_length:
            return content
        
        # Mantener el inicio y el final, comprimir el medio
        start_portion = max_length // 3
        end_portion = max_length // 3
        
        return (content[:start_portion] + 
                f"\n\n[...contenido comprimido - {len(content)} caracteres totales...]\n\n" + 
                content[-end_portion:])

    async def finance_qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages", [])
        
        # Limpiar y optimizar mensajes
        optimized_messages = clean_and_optimize_messages(messages)
        
        # Comprimir contenido muy largo si es necesario
        final_messages = []
        for msg in optimized_messages:
            if isinstance(msg, (HumanMessage, AIMessage)) and hasattr(msg, 'content'):
                content = str(msg.content) if msg.content else ""
                if len(content) > 5000:
                    compressed_content = compress_long_content(content)
                    
                    if isinstance(msg, HumanMessage):
                        new_msg = HumanMessage(content=compressed_content)
                    else:  # AIMessage
                        new_msg = AIMessage(content=compressed_content)
                        # Preservar tool_calls si existen
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            new_msg.tool_calls = msg.tool_calls
                    final_messages.append(new_msg)
                else:
                    final_messages.append(msg)
            else:
                final_messages.append(msg)
        
        # Logging mejorado
        print(f"📊 Optimización de mensajes:")
        print(f"   Original: {len(messages)} mensajes")
        print(f"   Optimizado: {len(final_messages)} mensajes")
        print(f"   Tipos: {[type(msg).__name__ for msg in final_messages]}")
        
        # Validación final de secuencias
        for i, msg in enumerate(final_messages):
            if isinstance(msg, ToolMessage):
                if i == 0 or not isinstance(final_messages[i-1], AIMessage):
                    print(f"⚠️  Advertencia: ToolMessage en posición {i} sin AIMessage previo")
        
        try:
            ai_msg = await llm.ainvoke(final_messages)
            return {"messages": [ai_msg]}
        except Exception as e:
            print(f"❌ Error en el LLM: {e}")
            # En caso de error, intentar con mensajes más básicos
            basic_messages = [
                SystemMessage(content=system_prompt),
                messages[-1] if messages else HumanMessage(content="¿Puedes ayudarme?")
            ]
            ai_msg = await llm.ainvoke(basic_messages)
            return {"messages": [ai_msg]}

    return finance_qa_node