import { initializeApp } from "firebase/app";

import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCn30tTlWFJSTA3xJnPuMxinAJn6NmLkcg",
  authDomain: "cortex-ai-a9079.firebaseapp.com",
  projectId: "cortex-ai-a9079",
  storageBucket: "cortex-ai-a9079.firebasestorage.app",
  messagingSenderId: "886288696897",
  appId: "1:886288696897:web:587f0ec0e417bee33f28c0",
  measurementId: "G-Y4LQYSQ4L2"

};


const app = initializeApp(firebaseConfig);


export const auth = getAuth(app);