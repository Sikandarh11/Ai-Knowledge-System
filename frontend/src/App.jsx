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





// App.jsx — Testing layout with dummy pages
// We add React Router routes here
// Each route = one page
import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'

// ── Dummy placeholder pages for testing ───────────
// 🔌 BACKEND: these will be replaced with real pages
//    in Step 5, 6, 7
const HomePage = () => (
  <div className="space-y-4">
    <div className="grid grid-cols-3 gap-4">
      {/* Dummy workspace cards */}
      {['Workspace 1', 'Workspace 2', 'Workspace 3'].map((w) => (
        <div key={w} className="
          bg-dark-700 rounded-xl p-6
          border border-dark-500
          hover:border-neon-purple
          transition-colors duration-200
          cursor-pointer
        ">
          <h3 className="text-white font-semibold">{w}</h3>
          <p className="text-slate-500 text-sm mt-1">3 documents</p>
        </div>
      ))}
    </div>
  </div>
)

const DocumentsPage = () => (
  <div className="space-y-4">
    <div className="bg-dark-700 rounded-xl p-6 border border-dark-500">
      <p className="text-slate-300">Documents page coming in Step 6</p>
    </div>
  </div>
)

const ChatPage = () => (
  <div className="space-y-4">
    <div className="bg-dark-700 rounded-xl p-6 border border-dark-500">
      <p className="text-slate-300">Chat page coming in Step 7</p>
    </div>
  </div>
)
// ── End dummy pages ────────────────────────────────

function App() {
  return (
    <Routes>
      {/* Each Route wraps page in Layout */}
      {/* Layout handles sidebar + topbar automatically */}

      <Route path="/" element={
        <Layout
          title="Home"
          showAction={true}
          actionLabel="New Workspace"
          onAction={() => alert('New Workspace clicked!')}
        >
          <HomePage />
        </Layout>
      } />

      <Route path="/documents" element={
        <Layout title="Documents">
          <DocumentsPage />
        </Layout>
      } />

      <Route path="/chat" element={
        <Layout title="Chat">
          <ChatPage />
        </Layout>
      } />

    </Routes>
  )
}

export default App
// ```

// ---

// ## What You Should See
// ```
// ✅ Dark sidebar on the left with logo
// ✅ Navigation links: Home, Documents, Chat
// ✅ Active link highlights in neon purple
// ✅ Topbar fixed at top with search bar
// ✅ "New Workspace" button on Home page
// ✅ Click nav links → page content changes
// ✅ Clicking Documents/Chat → shows placeholder text