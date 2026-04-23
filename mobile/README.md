VerifyAI (Expo)

This is a minimal Expo scaffold for the VerifyAI mobile app prototype.

Run (after installing dependencies):

```bash
cd mobile
npm install
npx expo start
```

Notes:
- Uses React Navigation (install required packages).
- `services/api.js` contains a mock `analyzeText` function returning mock JSON after 2s.
- Replace `OrbPlaceholder` with a Lottie/Rive component for production animations.

Recommended install (run inside `mobile`):

```bash
npx expo install react-native-gesture-handler react-native-reanimated react-native-screens react-native-safe-area-context
npm install @react-navigation/native @react-navigation/native-stack
```

Important: Reanimated requires the Babel plugin which is already added in `babel.config.js`.
