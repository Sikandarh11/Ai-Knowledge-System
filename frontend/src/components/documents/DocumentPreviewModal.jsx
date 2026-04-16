import Modal from '../ui/Modal'

const DocumentPreviewModal = ({ isOpen, onClose, document }) => {
  if (!document) {
    return null
  }

  const content = (document.content || '').trim()

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={document.filename || 'Document Preview'} size="xl">
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Type: {(document.file_type || 'txt').toUpperCase()}</span>
          <span>{document.chunk_count ?? 0} chunks</span>
        </div>

        <div className="max-h-[60vh] overflow-y-auto rounded-xl border border-dark-500 bg-dark-900 p-4">
          {content ? (
            <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-200 font-sans">
              {content}
            </pre>
          ) : (
            <p className="text-sm text-slate-500">No extracted content available for this document.</p>
          )}
        </div>
      </div>
    </Modal>
  )
}

export default DocumentPreviewModal
