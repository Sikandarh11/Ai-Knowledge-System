// function App() {
//   return (
//     <div className="min-h-screen bg-dark-900 flex items-center justify-center">
//       <div className="text-center space-y-4">

//         {/* Testing neon glow text color */}
//         <h1 className="text-4xl font-bold text-neon-glow text-glow">
//           Agentic-AI-Personal-Knowledge-System
//         </h1>

//         {/* Testing slate color */}
//         <p className="text-slate-400 text-lg">
//           Frontend is live
//         </p>


//         {/* Testing neon purple background */}
//         {/* <div className="w-32 h-1 bg-neon-purple mx-auto rounded-full shadow-neon-md" /> */}

//         {/* Testing card background color */}
//         {/* <div className="mt-4 p-4 bg-dark-700 rounded-xl neon-border">
//           <p className="text-neon-cyan text-sm">Muhammad(Neon cyan text)</p>
//           <p className="text-neon-purple text-sm mt-1">Hamza(Neon purple text)</p>
//           <p className="text-neon-glow text-sm mt-1">Waheed(Neon glow text)</p>
//         </div> */}

//       </div>
//     </div>
//   )
// }

// export default App


// Temporary test — testing all 3 ui components together
// We will replace this in Step 3 with real routing
// import { useState } from 'react'
// import Button from './components/ui/Button'
// import Loader from './components/ui/Loader'
// import Modal from './components/ui/Modal'

// function App() {
//   const [modalOpen, setModalOpen] = useState(false)
//   const [loading, setLoading] = useState(false)

//   // Simulate a loading action
//   const handleLoadingTest = () => {
//     setLoading(true)
//     setTimeout(() => setLoading(false), 2000) // stops after 2 seconds
//   }

//   return (
//     <div className="min-h-screen bg-dark-900 flex items-center justify-center">
//       <div className="text-center space-y-6">

//         <h1 className="text-4xl font-bold text-neon-glow text-glow">
//           🧠 AI Knowledge System
//         </h1>
//         <p className="text-slate-400">Step 2 — UI Components Test</p>

//         {/* ── Testing all button variants ─────────── */}
//         <div className="flex gap-3 justify-center flex-wrap">
//           <Button variant="primary">Primary Button</Button>
//           <Button variant="secondary">Secondary</Button>
//           <Button variant="danger">Danger</Button>
//           <Button variant="ghost">Ghost</Button>
//           <Button variant="primary" loading={true}>Loading</Button>
//           <Button variant="primary" disabled={true}>Disabled</Button>
//         </div>

//         {/* ── Testing loader sizes ─────────────────── */}
//         <div className="flex gap-6 justify-center items-center">
//           <Loader size="sm" />
//           <Loader size="md" />
//           <Loader size="lg" />
//           <Loader size="md" text="Loading data..." />
//         </div>

//         {/* ── Testing loading button ───────────────── */}
//         <Button
//           variant="primary"
//           size="lg"
//           loading={loading}
//           onClick={handleLoadingTest}
//         >
//           {loading ? 'Loading...' : 'Test Loading State'}
//         </Button>

//         {/* ── Testing modal ────────────────────────── */}
//         <div>
//           <Button
//             variant="primary"
//             onClick={() => setModalOpen(true)}
//           >
//             Open Test Modal
//           </Button>

//           <Modal
//             isOpen={modalOpen}
//             onClose={() => setModalOpen(false)}
//             title="Test Modal ✅"
//             size="md"
//           >
//             <p className="text-slate-300">
//               This is the modal content area.
//               Click outside or press Esc to close.
//             </p>
//             <div className="flex gap-3 mt-6 justify-end">
//               <Button
//                 variant="secondary"
//                 onClick={() => setModalOpen(false)}
//               >
//                 Cancel
//               </Button>
//               <Button variant="primary">
//                 Confirm
//               </Button>
//             </div>
//           </Modal>
//         </div>

//       </div>
//     </div>
//   )
// }

// export default App
// // ```

// // ---

// // ## What You Should See
// // ```
// // ✅ 6 different button styles
// // ✅ 3 spinner sizes + one with text
// // ✅ Click "Test Loading" → spinner appears for 2 seconds
// // ✅ Click "Open Test Modal" → dark overlay + modal popup
// // ✅ Press Escape or click outside → modal closes





// // App.jsx — Testing layout with dummy pages
// // We add React Router routes here
// // Each route = one page
// import { Routes, Route } from 'react-router-dom'
// import Layout from './components/layout/Layout'

// // ── Dummy placeholder pages for testing ───────────
// // 🔌 BACKEND: these will be replaced with real pages
// //    in Step 5, 6, 7
// const HomePage = () => (
//   <div className="space-y-4">
//     <div className="grid grid-cols-3 gap-4">
//       {/* Dummy workspace cards */}
//       {['Workspace 1', 'Workspace 2', 'Workspace 3'].map((w) => (
//         <div key={w} className="
//           bg-dark-700 rounded-xl p-6
//           border border-dark-500
//           hover:border-neon-purple
//           transition-colors duration-200
//           cursor-pointer
//         ">
//           <h3 className="text-white font-semibold">{w}</h3>
//           <p className="text-slate-500 text-sm mt-1">3 documents</p>
//         </div>
//       ))}
//     </div>
//   </div>
// )

// const DocumentsPage = () => (
//   <div className="space-y-4">
//     <div className="bg-dark-700 rounded-xl p-6 border border-dark-500">
//       <p className="text-slate-300">Documents page coming in Step 6</p>
//     </div>
//   </div>
// )

// const ChatPage = () => (
//   <div className="space-y-4">
//     <div className="bg-dark-700 rounded-xl p-6 border border-dark-500">
//       <p className="text-slate-300">Chat page coming in Step 7</p>
//     </div>
//   </div>
// )
// // ── End dummy pages ────────────────────────────────

// function App() {
//   return (
//     <Routes>
//       {/* Each Route wraps page in Layout */}
//       {/* Layout handles sidebar + topbar automatically */}

//       <Route path="/" element={
//         <Layout
//           title="Home"
//           showAction={true}
//           actionLabel="New Workspace"
//           onAction={() => alert('New Workspace clicked!')}
//         >
//           <HomePage />
//         </Layout>
//       } />

//       <Route path="/documents" element={
//         <Layout title="Documents">
//           <DocumentsPage />
//         </Layout>
//       } />

//       <Route path="/chat" element={
//         <Layout title="Chat">
//           <ChatPage />
//         </Layout>
//       } />

//     </Routes>
//   )
// }

// export default App
// // ```

// // ---

// // ## What You Should See
// // ```
// // ✅ Dark sidebar on the left with logo
// // ✅ Navigation links: Home, Documents, Chat
// // ✅ Active link highlights in neon purple
// // ✅ Topbar fixed at top with search bar
// // ✅ "New Workspace" button on Home page
// // ✅ Click nav links → page content changes
// // ✅ Clicking Documents/Chat → shows placeholder text




// // Testing that API functions work with dummy data
// // Open browser console to see the logs
// import { Routes, Route } from 'react-router-dom'
// import { useEffect } from 'react'
// import Layout from './components/layout/Layout'
// import { getWorkspaces, createWorkspace } from './api/workspaces'
// import { getDocuments } from './api/documents'
// import { queryDocuments } from './api/query'
// import { sendChatMessage } from './api/chat'

// const HomePage = () => {
//   useEffect(() => {
//     const testAPIs = async () => {
//       console.log('─── Testing API Layer ───')

//       const workspaces = await getWorkspaces()
//       console.log('✅ getWorkspaces:', workspaces)

//       const newWs = await createWorkspace('Test Workspace')
//       console.log('✅ createWorkspace:', newWs)

//       const docs = await getDocuments(1)
//       console.log('✅ getDocuments:', docs)

//       const answer = await queryDocuments(1, 'What is this about?')
//       console.log('✅ queryDocuments:', answer)

//       const chat = await sendChatMessage(1, 'Hello!')
//       console.log('✅ sendChatMessage:', chat)

//       console.log('─── All API tests passed! ───')
//     }
//     testAPIs()
//   }, [])

//   return (
//     <div className="space-y-4">
//       <div className="bg-dark-700 rounded-xl p-6 border border-dark-500">
//         <p className="text-neon-glow font-semibold">
//           ✅ API Layer Test — Check F12 Console
//         </p>
//         <p className="text-slate-400 text-sm mt-2">
//           All 5 API functions are being called with dummy data.
//           Open DevTools → Console to see the results.
//         </p>
//       </div>
//     </div>
//   )
// }

// function App() {
//   return (
//     <Routes>
//       <Route path="/" element={
//         <Layout
//           title="Home"
//           showAction={true}
//           actionLabel="New Workspace"
//           onAction={() => console.log('New Workspace clicked')}
//         >
//           <HomePage />
//         </Layout>
//       } />
//       <Route path="/documents" element={
//         <Layout title="Documents">
//           <div className="text-slate-400">Coming in Step 6</div>
//         </Layout>
//       } />
//       <Route path="/chat" element={
//         <Layout title="Chat">
//           <div className="text-slate-400">Coming in Step 7</div>
//         </Layout>
//       } />
//     </Routes>
//   )
// }

// export default App


// // ---

// // ## What You Should See

// // In the browser at `http://localhost:5173`:
// // ```
// // ✅ API Layer Test card showing
// // ```

// // In **F12 Console**:
// // ```
// // 📤 API Request: GET /workspaces    ← from interceptor (only when real backend)
// // ✅ getWorkspaces: [{...}, {...}, {...}]
// // ✅ createWorkspace: { id: ..., name: 'Test Workspace' }
// // ✅ getDocuments: [{...}, {...}, {...}]
// // ✅ queryDocuments: { answer: '...', sources: [...] }
// // ✅ sendChatMessage: { response: '...', sources: [...] }
// // ─── All API tests passed! ───






// // App.jsx — Updated with real HomePage
// // Removed test code, using real page now
// import { Routes, Route } from 'react-router-dom'
// import { Toaster } from 'react-hot-toast'
// import Layout from './components/layout/Layout'
// import HomePage from './pages/HomePage'

// function App() {
//   return (
//     <>
//       {/* Toaster shows success/error notifications */}
//       {/* position top-right = notifications appear top right */}
//       <Toaster
//         position="top-right"
//         toastOptions={{
//           style: {
//             background: '#1a1a24',
//             color: '#e2e8f0',
//             border: '1px solid #32324a',
//           },
//           success: {
//             iconTheme: {
//               primary: '#7c3aed',
//               secondary: '#fff',
//             },
//           },
//         }}
//       />

//       <Routes>
//         {/* Home — workspace list */}
//         <Route path="/" element={
//           <Layout title="Home">
//             <HomePage />
//           </Layout>
//         } />

//         {/* Documents — coming Step 6 */}
//         <Route path="/documents" element={
//           <Layout title="Documents">
//             <div className="text-slate-400 p-6">
//               Documents page coming in Step 6
//             </div>
//           </Layout>
//         } />

//         {/* Chat — coming Step 7 */}
//         <Route path="/chat" element={
//           <Layout title="Chat">
//             <div className="text-slate-400 p-6">
//               Chat page coming in Step 7
//             </div>
//           </Layout>
//         } />
//       </Routes>
//     </>
//   )
// }

// export default App
// // ```

// // ---

// // ## What You Should See
// // ```
// // ✅ 3 dummy workspace cards in a grid
// // ✅ Each card shows name, date, document count
// // ✅ Hover card → border glows purple, delete icon appears
// // ✅ Click "New Workspace" → modal opens
// // ✅ Type name → click Create → new card appears + toast notification
// // ✅ Click delete icon → card disappears + toast notification
// // ✅ Click "Open Workspace" → navigates to /documents
// // ✅ Empty state shows when all workspaces deleted





// import { Routes, Route } from 'react-router-dom'
// import { Toaster } from 'react-hot-toast'
// import Layout from './components/layout/Layout'
// import HomePage from './pages/HomePage'
// import DocumentsPage from './pages/DocumentsPage'

// function App() {
//   return (
//     <>
//       <Toaster
//         position="top-right"
//         toastOptions={{
//           style: {
//             background: '#1a1a24',
//             color: '#e2e8f0',
//             border: '1px solid #32324a',
//           },
//           success: {
//             iconTheme: { primary: '#7c3aed', secondary: '#fff' },
//           },
//         }}
//       />
//       <Routes>
//         <Route path="/" element={
//           <Layout title="Home">
//             <HomePage />
//           </Layout>
//         } />

//         <Route path="/documents" element={
//           <Layout title="Documents">
//             <DocumentsPage />
//           </Layout>
//         } />

//         <Route path="/chat" element={
//           <Layout title="Chat">
//             <div className="text-slate-400 p-6">
//               Chat page coming in Step 7
//             </div>
//           </Layout>
//         } />
//       </Routes>
//     </>
//   )
// }

// export default App
// // ```

// // ---

// // ## What You Should See
// // ```
// // ✅ Click "Open Workspace" on any card → goes to Documents page
// // ✅ Documents listed with PDF/DOCX/TXT color badges
// // ✅ Chunk count and date shown per document
// // ✅ Hover document → delete icon appears
// // ✅ Click "Upload Document" → drag & drop modal opens
// // ✅ Drop a file → file preview shows
// // ✅ Click "Upload & Process" → success message → modal closes
// // ✅ New document appears in list
// // ✅ Back arrow → returns to HomePage




import { useEffect, useRef } from 'react'
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Toaster, toast } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import DocumentsPage from './pages/DocumentsPage'
import ChatPage from './pages/ChatPage'
import AuthPage from './pages/AuthPage'
import { clearToken } from './api/auth'

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000
const LAST_ACTIVITY_KEY = 'last_activity_at'

const hasAuthToken = () => {
  const token = localStorage.getItem('access_token')
  if (!token) {
    return false
  }

  const lastActivity = Number(localStorage.getItem(LAST_ACTIVITY_KEY))
  if (!lastActivity) {
    clearToken()
    return false
  }

  if (lastActivity && Date.now() - lastActivity > INACTIVITY_TIMEOUT_MS) {
    clearToken()
    localStorage.removeItem(LAST_ACTIVITY_KEY)
    return false
  }

  return true
}

const ProtectedRoute = ({ children }) => {
  if (!hasAuthToken()) {
    return <Navigate to="/auth" replace />
  }
  return children
}

const PublicAuthRoute = ({ children }) => {
  if (hasAuthToken()) {
    return <Navigate to="/" replace />
  }
  return children
}

function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const timeoutRef = useRef(null)

  useEffect(() => {
    if (!hasAuthToken()) {
      return
    }

    const logoutForInactivity = () => {
      if (!hasAuthToken()) {
        return
      }

      clearToken()
      localStorage.removeItem(LAST_ACTIVITY_KEY)
      toast.error('Session expired due to inactivity. Please login again.')
      navigate('/auth', { replace: true })
    }

    const resetInactivityTimer = () => {
      localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()))
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      timeoutRef.current = setTimeout(logoutForInactivity, INACTIVITY_TIMEOUT_MS)
    }

    const activityEvents = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart']
    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, resetInactivityTimer, { passive: true })
    })

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        resetInactivityTimer()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    resetInactivityTimer()

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, resetInactivityTimer)
      })
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [location.pathname, navigate])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1a1a24',
            color: '#e2e8f0',
            border: '1px solid #32324a',
          },
          success: {
            iconTheme: { primary: '#7c3aed', secondary: '#fff' },
          },
        }}
      />
      <Routes>
        <Route path="/auth" element={
          <PublicAuthRoute>
            <AuthPage />
          </PublicAuthRoute>
        } />

        <Route path="/" element={
          <ProtectedRoute>
            <Layout title="Home">
              <HomePage />
            </Layout>
          </ProtectedRoute>
        } />

        <Route path="/documents" element={
          <ProtectedRoute>
            <Layout title="Documents">
              <DocumentsPage />
            </Layout>
          </ProtectedRoute>
        } />

        <Route path="/chat" element={
          <ProtectedRoute>
            <Layout title="Chat">
              <ChatPage />
            </Layout>
          </ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to={hasAuthToken() ? '/' : '/auth'} replace />} />
      </Routes>
    </>
  )
}

export default App
// ```

// ---

// ## What You Should See
// ```
// ✅ Chat page opens with welcome screen
// ✅ Workspace selector dropdown at top
// ✅ Suggested questions shown when chat empty
// ✅ Type message → press Enter → user bubble appears right
// ✅ "Thinking..." loader appears while waiting
// ✅ AI response appears left with markdown rendering
// ✅ Source document badges shown below AI response
// ✅ Clear Chat button appears after first message
// ✅ Switch workspace → chat clears automatically