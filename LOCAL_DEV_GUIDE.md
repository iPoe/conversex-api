# 🛠️ Guía de Desarrollo Local con Supabase

Esta guía explica cómo sincronizar tu entorno local de Supabase con el esquema y las funciones (RPC) que ya existen en el proyecto de la nube. Es **crítico** seguir estos pasos si encuentras errores como `500 Internal Server Error` o `Function not found in schema cache`.

## 🔄 Sincronizando la Réplica de la Nube (Cloud Replica)

Cuando inicias Supabase localmente con `supabase start`, la base de datos arranca vacía. Para traer todas las tablas, relaciones y funciones personalizadas (como `commit_player_move`), sigue este flujo:

### 1. Autenticación
Primero, asegúrate de que tu CLI tiene acceso a tu cuenta de Supabase.
```bash
npx supabase login
```

### 2. Vincular el Proyecto
Conecta tu directorio local con el proyecto remoto. Necesitarás el **Project ID** (disponible en la URL de tu dashboard de Supabase: `https://supabase.com/dashboard/project/<TU_PROJECT_REF>`).
```bash
npx supabase link --project-ref <TU_PROJECT_REF>
```
*Nota: Se te pedirá la contraseña de la base de datos que configuraste al crear el proyecto en la nube.*

### 3. Descargar el Esquema Remoto (Pull)
Este comando compara tu base de datos local con la remota y descarga todas las definiciones (Tablas, RPCs, Triggers) a la carpeta `supabase/migrations/`.
```bash
npx supabase db pull
```

### 4. Reiniciar y Aplicar Cambios localmente
Una vez descargadas las migraciones, fuerza a tu instancia local de Docker a reconstruirse usando estos nuevos archivos.
```bash
npx supabase db reset
```
*Este comando borrará los datos locales actuales y aplicará todo el esquema desde cero.*

---

## ⚠️ Troubleshooting (Solución de Problemas)

### "Function not found in schema cache"
Si la API devuelve un error indicando que no encuentra una función RPC (ej. `commit_player_move`), significa que tu base de datos local está desactualizada respecto al código de la API.
**Solución:** Ejecuta los pasos **3 (Pull)** y **4 (Reset)** de esta guía.

### Errores de Conexión con Docker
Asegúrate de que Docker Desktop esté corriendo antes de ejecutar cualquier comando de `supabase`. Si los contenedores fallan:
```bash
npx supabase stop
npx supabase start
```

### Datos de Prueba (Seeding)
Después de un `db reset`, las tablas estarán vacías. No olvides volver a cargar los casos de juego:
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 scripts/seed_cases_from_excel.py
```
