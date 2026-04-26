# 🔭 Global Insight Engine — Android APK

AI-powered аналитическое приложение. Анализирует любую тему по 6 измерениям:
геополитика, экономика, технологии, общество, риски, прогноз.

---

## 📱 Как получить APK (3 способа)

### Способ 1: GitHub Actions (рекомендуется, 5 минут)

1. Создайте аккаунт на [github.com](https://github.com) (бесплатно)
2. Нажмите **New repository** → назовите `global-insight-engine` → Create
3. Загрузите все файлы из этой папки в репозиторий
4. Перейдите в **Actions** → выберите **Build APK** → нажмите **Run workflow**
5. Через 3-5 минут в разделе **Releases** появится готовый APK
6. Скачайте `GlobalInsightEngine-debug.apk` на телефон и установите

### Способ 2: Android Studio (на компьютере)

1. Установите [Android Studio](https://developer.android.com/studio)
2. Откройте эту папку как проект: **File → Open**
3. Подождите синхронизацию Gradle (~2-3 минуты)
4. **Build → Build Bundle(s)/APK(s) → Build APK(s)**
5. Готовый APK появится в `app/build/outputs/apk/debug/`
6. Переброcьте файл на телефон и установите

### Способ 3: Установить как PWA (без APK, мгновенно)

Если у вас есть хостинг (Replit, Vercel, GitHub Pages):
1. Загрузите файл `app/src/main/assets/index.html`
2. Откройте сайт в Chrome на Android
3. Нажмите **⋮ → Добавить на главный экран**
4. Приложение появится как иконка, работает как APK

---

## 📲 Установка APK на телефон

1. Перенесите APK-файл на телефон (через USB, Telegram, Google Drive)
2. Откройте файл менеджер → найдите APK → нажмите на него
3. Если появится предупреждение — нажмите **Настройки** → включите **Установка из неизвестных источников**
4. Вернитесь и нажмите **Установить**

---

## ⚙️ Требования

- Android 6.0+ (API 23+)
- Интернет (для обращения к Claude API)
- ~5 МБ свободного места

---

## 🏗️ Структура проекта

```
GlobalInsightAPK/
├── app/
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── assets/
│   │   │   └── index.html          ← Всё приложение здесь
│   │   ├── java/com/globalinsight/
│   │   │   └── MainActivity.java   ← WebView обёртка
│   │   └── res/
│   │       ├── values/styles.xml
│   │       └── mipmap-*/           ← Иконки
│   └── build.gradle
├── .github/workflows/build.yml     ← Автосборка APK
├── build.gradle
└── settings.gradle
```

---

## 🔧 Кастомизация

Все изменения делаются в одном файле: `app/src/main/assets/index.html`

Чтобы обновить приложение:
- Отредактируйте `index.html`
- Пересоберите APK или просто обновите хостинг (для PWA)
