// Layout.jsx — The master wrapper
// Every page is wrapped in this component
// It puts Sidebar on left, Topbar on top, page content in the middle
// 
// Usage in App.jsx:
// <Layout title="Home">
//   <HomePage />
// </Layout>

import Sidebar from './Sidebar'
import Topbar from './Topbar'

const Layout = ({
  children,           // the page content
  title,              // page title shown in topbar
  onAction,           // action button handler
  actionLabel,        // action button label
  showAction = false, // show action button?
}) => {
  return (
    // min-h-screen = at least full height
    <div className="min-h-screen bg-dark-900">

      {/* Fixed sidebar on left */}
      <Sidebar />

      {/* Fixed topbar on top right */}
      <Topbar
        title={title}
        onAction={onAction}
        actionLabel={actionLabel}
        showAction={showAction}
      />

      {/* ── Main Content Area ─────────────────────────
          ml-64 = shift right to avoid sidebar overlap
          pt-16 = shift down to avoid topbar overlap
          p-6   = inner padding for content
      ─────────────────────────────────────────────── */}
      <main className="ml-64 pt-16 p-6 min-h-screen">
        {children}
      </main>

    </div>
  )
}

export default Layout