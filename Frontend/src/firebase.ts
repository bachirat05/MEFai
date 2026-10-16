import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth"; 
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyAgmUxS8foF7tsytvV9b2g0z0cZ_HWL5aM",
  authDomain: "mefai-9de25.firebaseapp.com",
  projectId: "mefai-9de25",
  storageBucket: "mefai-9de25.firebasestorage.app",
  messagingSenderId: "1026406474174",
  appId: "1:1026406474174:web:0b834d37ac101de7b319ef",
  measurementId: "G-JLHX9Y07PW"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);