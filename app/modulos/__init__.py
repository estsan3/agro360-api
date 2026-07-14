"""Módulos de negocio de Agro360.

Cada subpaquete es un módulo autónomo con la misma estructura interna:

    modulo/
    ├── router.py     → capa API: endpoints FastAPI (HTTP puro, sin negocio)
    ├── schemas.py    → DTOs Pydantic de entrada/salida
    ├── service.py    → capa SERVICE: casos de uso y límites transaccionales
    ├── bo.py         → capa BO (Business Object): reglas de negocio puras
    ├── dao.py        → capa DAO: acceso a datos (SQLAlchemy)
    ├── models.py     → modelos ORM (tablas con prefijo del módulo)
    └── contrato.py   → interfaz pública que otros módulos pueden consumir

Reglas de dependencia (para poder extraer módulos como microservicios):

1. Un módulo NUNCA importa el service/bo/dao/models de otro módulo.
2. Si necesita datos de otro módulo, usa su `contrato.py` (interfaz).
3. Para notificar sin acoplarse, publica eventos en `core.eventos`.
4. `core` no importa módulos (salvo el registro de modelos en database).
"""
