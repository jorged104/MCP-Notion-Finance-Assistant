from typing import Dict, Any
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage


def make_finance_classifier_node(llm: BaseLanguageModel, finance_catalog_json: list[str]):
    catalogs_block = "\n".join(finance_catalog_json)
    today = datetime.today().strftime("%Y-%m-%d")
    system_prompt = f"""Eres Finance-Expert-Classify, especialista en procesar extractos bancarios y gestionar transacciones financieras.

📂 **Catálogos disponibles**:
----------
{catalogs_block}
----------

### 🧠 PROTOCOLO DE PROCESAMIENTO:

**FASE 1 - EXTRACCIÓN (cuando recibes un extracto nuevo):**
- Identifica a que cuenta pertenece el extracto - ese sera el origen de las transacciones
- Extrae TODAS las transacciones del extracto bancario
- Usa las herramientas para insertar cada transacción
- Clasifica según los catálogos disponibles
- Después de llamar herramientas, espera los resultados

**FASE 2 - VERIFICACIÓN (después de ejecutar herramientas):**
- Revisa los resultados de las inserciones en el historial de mensajes
- Verifica que todas las transacciones se procesaron correctamente
- Identifica si hay errores en las inserciones
- Si faltan transacciones por procesar, regresa a FASE 1
- Si todas están procesadas correctamente, pasa a FASE 3

**FASE 3 - FINALIZACIÓN:**
- Proporciona un resumen final de las transacciones procesadas
- Incluye: número total de transacciones, tipos de transacciones, montos totales
- Confirma al usuario que el procesamiento está completo
- **CRÍTICO: NO llames más herramientas en esta fase**

### 🔍 CÓMO IDENTIFICAR EN QUÉ FASE ESTÁS:

1. **¿Hay un extracto nuevo sin procesar?** → FASE 1 (Extracción)
2. **¿Acabas de recibir respuestas de herramientas de inserción?** → FASE 2 (Verificación)
3. **¿Ya verificaste que todas las transacciones están procesadas?** → FASE 3 (Finalización)

### 📋 INDICADORES CLAROS POR FASE:

**FASE 1 - Responde:** "Iniciando extracción de transacciones..." + usar herramientas
**FASE 2 - Responde:** "Verificando inserciones..." + revisar resultados + decidir siguiente paso
**FASE 3 - Responde:** "Procesamiento completado. Resumen final:" + NO MÁS HERRAMIENTAS

### 💡 Reglas especiales de clasificación:
- Si la descripción contiene patrones como `1/25`, `2/12`, etc., clasifica como **"Cuotas"** o **"Gasto Recurrente"**
- Si el monto tiene símbolo `$` o proviene de una columna marcada en **dólares**, convierte el valor a **quetzales** multiplicando por **8**
- Fechas: usa formato YYYY-MM-DD
- Tipos de transacción comunes: "Debito", "Ingreso"

### ⚠️ REGLAS CRÍTICAS:
1. **No dupliques transacciones**: verifica el historial antes de insertar
2. **En FASE 3, NUNCA uses herramientas**, solo proporciona el resumen final
3. **Sé explícito** sobre en qué fase estás en cada respuesta
4. **Revisa cuidadosamente** los resultados de las herramientas antes de continuar

### 📊 FORMATO DE RESUMEN FINAL (FASE 3):
```
Procesamiento completado exitosamente.

📊 RESUMEN FINAL:
- Total de transacciones procesadas: X
- Gastos: X transacciones por Q.XXX
- Ingresos: X transacciones por Q.XXX  
- Transferencias: X transacciones por Q.XXX
- Errores encontrados: X (detalle si los hay)

✅ Todas las transacciones del extracto han sido insertadas en la base de datos.
```

Fecha actual: {today}

Recuerda: Identifica tu fase actual, actúa según el protocolo y sé claro sobre tu estado.
"""

    async def finance_classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = [SystemMessage(content=system_prompt)]
        
        # Incluir TODO el historial para que el modelo tenga contexto completo
        if state.get("messages"):
            messages.extend(state["messages"])

        # Solo agregar el markdown si es la primera vez que lo procesamos
        if md := state.get("markdown"):
            # Verificar si ya se procesó este extracto mirando el historial
            already_processed = any(
                "Iniciando extracción de transacciones" in str(msg.content) if hasattr(msg, 'content') else False
                for msg in state.get("messages", [])
            )
            
            if not already_processed:
                print("📄 Extracto bancario recibido para procesar")
                print(md[:200] + "..." if len(md) > 200 else md)
                messages.append(HumanMessage(content=f"### NUEVO EXTRACTO BANCARIO PARA PROCESAR:\n\n{md.strip()}"))

        response = await llm.ainvoke(messages)

        return {
            "messages": [response]
        }

    return finance_classifier_node


# FUNCIÓN DE CONDICIÓN PERSONALIZADA para detectar cuándo terminar
def finance_phase_condition(state):
    """
    Determina si el classifier debe llamar tools o terminar basándose en las fases
    """
    last_message = state["messages"][-1] if state.get("messages") else None
    
    if not last_message:
        return "END"
    
    # Si el último mensaje tiene tool_calls, ejecutar herramientas
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Verificar si el mensaje indica que estamos en FASE 3 (finalización)
    if hasattr(last_message, 'content') and last_message.content:
        content = last_message.content.lower()
        
        # Indicadores de que estamos en FASE 3 y debemos terminar
        completion_indicators = [
            "procesamiento completado",
            "resumen final:",
            "✅ todas las transacciones",
            "fase 3",
            "finalización completada"
        ]
        
        if any(indicator in content for indicator in completion_indicators):
            print("🏁 Detectado: Proceso en FASE 3 - Terminando")
            return "END"
    
    # Si no hay tool_calls y no está en fase 3, algo puede estar mal, terminar
    return "END"
