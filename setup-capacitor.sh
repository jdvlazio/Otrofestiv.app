#!/bin/bash
echo "=== Otrofestiv — Setup Capacitor ==="

# 1. Instalar dependencias
echo "→ Instalando dependencias..."
npm install

# 2. Inicializar Capacitor (ya configurado en capacitor.config.json)
echo "→ Inicializando Capacitor..."
npx cap init --web-dir . app.otrofestiv "Otrofestiv" 2>/dev/null || true

# 3. Agregar plataforma Android
echo "→ Agregando Android..."
npx cap add android

# 4. Sincronizar
echo "→ Sincronizando..."
npx cap sync android

echo ""
echo "✓ Listo. Ahora ejecuta:"
echo "  npx cap open android"
echo ""
echo "Android Studio se abrirá con el proyecto."
echo "Presiona ▶ (Run) para instalar en tu dispositivo o emulador."
