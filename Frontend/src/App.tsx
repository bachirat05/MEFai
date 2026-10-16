import {
  useEffect,
  useState,
} from "react";

import {
  onAuthStateChanged,
  signOut,
  type User,
} from "firebase/auth";

import {
  Sparkles,
} from "lucide-react";

import { auth } from "./firebase";
import Login from "./Login";

import AdminDashboard from "./components/Admin/AdminDashboard";
import AuditLogsPage from "./components/Admin/AuditLogsPage";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import ChatPanel from "./components/Chat/ChatPanel";

import { useChat } from "./hooks/useChat";

import LeaveRequestForm from "./components/Leave/LeaveRequestForm";

import type { AppPage, UserRole } from "./types";
import MyRequests from "./components/Requests/MyRequests";

import ManagerDashboard from "./components/Manager/ManagerDashboard";

import DocumentsPage from "./components/Documents/DocumentsPage";
import SettingsPage from "./components/Settings/SettingsPage";
import DashboardPage from "./components/Dashboard/DashboardPage";

/* =========================================================
   TYPES
========================================================= */



/* =========================================================
   APP
========================================================= */

function App() {
  /* =======================================================
     AUTHENTICATION
  ======================================================= */

  const [user, setUser] =
    useState<User | null>(null);

  const [authLoading, setAuthLoading] =
    useState<boolean>(true);

  const [role, setRole] =
    useState<UserRole>("employee");

  const isAdmin = role === "admin";
  const isManager = role === "manager";

  const [activePage, setActivePage] =
    useState<AppPage>("chat");

  const [isSidebarCollapsed, setIsSidebarCollapsed] =
    useState(false);

  /* =======================================================
     CHAT HOOK
  ======================================================= */

  const {
    message,
    setMessage,

    isLoading,

    conversations,

    activeConversationId,
    setActiveConversationId,

    messages,
    messagesEndRef,

    createNewConversation,
    sendMessage,
    handleKeyDown,
    copyMessage,
    deleteExistingConversation,
  } = useChat({
    user,
  });

  /* =======================================================
     FIREBASE AUTH STATE
  ======================================================= */

  useEffect(() => {
    const unsubscribe =
      onAuthStateChanged(
        auth,
        async (
          currentUser: User | null
        ) => {
          setUser(currentUser);

          if (!currentUser) {
            setRole("employee");
            setActivePage("chat");
            setAuthLoading(false);

            return;
          }

          try {
            const tokenResult =
              await currentUser.getIdTokenResult();

            const firebaseRole =
              tokenResult.claims.role;

            const resolvedRole =
              firebaseRole === "admin" ||
              firebaseRole === "manager"
                ? firebaseRole
                : "employee";

            setRole(
              resolvedRole
            );

            setActivePage(
              resolvedRole === "admin"
                ? "dashboard"
                : "chat"
            );

            console.log(
              "Firebase user:",
              currentUser.email
            );

            console.log(
              "Firebase role:",
              firebaseRole
            );
          } catch (error) {
            console.error(
              "Impossible de récupérer le rôle Firebase:",
              error
            );

            setRole("employee");
            setActivePage("chat");
          } finally {
            setAuthLoading(false);
          }
        }
      );

    return unsubscribe;
  }, []);

  useEffect(() => {
    if (
      (
        activePage === "dashboard" ||
        activePage === "admin" ||
        activePage === "documents" ||
        activePage === "audit"
      ) &&
      !isAdmin
    ) {
      setActivePage("chat");
    }

    if (
      activePage === "manager" &&
      !isManager
    ) {
      setActivePage("chat");
    }
  }, [
    activePage,
    isAdmin,
    isManager,
  ]);

  /* =======================================================
     AUTO SCROLL
  ======================================================= */

  useEffect(() => {
    if (activePage !== "chat") {
      return;
    }

    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [
    messages,
    isLoading,
    activePage,
    messagesEndRef,
  ]);

  /* =======================================================
     LOGOUT
  ======================================================= */

  const handleLogout =
    async (): Promise<void> => {
      try {
        await signOut(auth);
      } catch (error) {
        console.error(
          "Logout error:",
          error
        );
      }
    };

  /* =======================================================
     AUTH LOADING
  ======================================================= */

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#f8f7fb]">
        <div className="flex flex-col items-center gap-4">

          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-600 text-white shadow-lg">
            <Sparkles size={25} />
          </div>

          <div className="flex items-center gap-2">

            <span className="h-2 w-2 animate-bounce rounded-full bg-violet-500" />

            <span
              className="h-2 w-2 animate-bounce rounded-full bg-violet-500"
              style={{
                animationDelay:
                  "150ms",
              }}
            />

            <span
              className="h-2 w-2 animate-bounce rounded-full bg-violet-500"
              style={{
                animationDelay:
                  "300ms",
              }}
            />

          </div>

          <p className="text-sm text-slate-500">
            Vérification de la connexion...
          </p>

        </div>
      </div>
    );
  }
  

  /* =======================================================
     NOT AUTHENTICATED
  ======================================================= */

  if (!user) {
    return <Login />;
  }

  /* =======================================================
     AUTHENTICATED APPLICATION
  ======================================================= */

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-800">

      {/* =================================================
          SIDEBAR
      ================================================= */}

      <Sidebar
        user={user}
        isAdmin={isAdmin}
        isManager={isManager}
        activePage={activePage}
        conversations={
          conversations
        }
        activeConversationId={
          activeConversationId
        }
        isCollapsed={isSidebarCollapsed}
        onNewConversation={() => {
          void createNewConversation();
          setActivePage("chat");
        }}
        onDeleteConversation={(id) => {
          void deleteExistingConversation(id);
        }}
        onSelectPage={
          setActivePage
        }
        onSelectConversation={(
          id
        ) => {
          void setActiveConversationId(
            id
          );

          setActivePage(
            "chat"
          );
        }}
        onLogout={() => {
          void handleLogout();
        }}
      />

      {/* =================================================
          MAIN
      ================================================= */}

      <main className="flex min-w-0 flex-1 flex-col">

        {/* HEADER */}

        <Header
          user={user}
          role={role}
          isAdmin={isAdmin}
          activePage={
          activePage
          }
          conversations={conversations}
          onToggleSidebar={() => {
            setIsSidebarCollapsed((value) => !value);
          }}
          onSelectPage={setActivePage}
          onSelectConversation={(id) => {
            void setActiveConversationId(id);
            setActivePage("chat");
          }}
        />

        {/* =================================================
            PAGE
        ================================================= */}
        {activePage === "dashboard" && isAdmin ? (
          <DashboardPage
            user={user}
            role={role}
            isAdmin={isAdmin}
            isManager={isManager}
            conversations={conversations}
            onSelectPage={setActivePage}
            onSelectConversation={(id) => {
              void setActiveConversationId(id);
              setActivePage("chat");
            }}
          />

        ) : activePage === "admin" && isAdmin ? (

          <AdminDashboard
            user={user} 
          />      
        ) : activePage === "manager" && isManager ? (
          <ManagerDashboard 
            user={user}
          />


        
        ) : activePage === "leave" ? (
          
          <LeaveRequestForm 
            user={user} 
            onSelectPage={setActivePage}
          />
          ) : activePage === "requests" ? (
            <MyRequests
              user={user}
              onSelectPage={setActivePage}
            />

        ) : activePage === "documents" && isAdmin ? (
          <DocumentsPage user={user} />
          ) : activePage === "audit" && isAdmin ? (
            <AuditLogsPage user={user} />
          ) : activePage === "settings" ? (
            <SettingsPage user={user}
            isAdmin={isAdmin}
            />
        ) : (
          <ChatPanel
            messages={messages}
            message={message}
            isLoading={isLoading}
            messagesEndRef={messagesEndRef}
            onMessageChange={setMessage}
            onSend={() => {
              void sendMessage();
            }}
            onKeyDown={handleKeyDown}
            onCopy={(content) => {
              void copyMessage(content);
            }}
          />

        )}

      </main>

    </div>
  );
}

export default App;
