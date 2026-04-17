import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import DocumentUpload from '../components/Document/DocumentUpload'

export default function UploadPage() {
  const navigate = useNavigate()
  return (
    <Layout title="Subir documento">
      <div className="max-w-lg mx-auto">
        <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border)] rounded-[var(--radius-xl)] p-6">
          <DocumentUpload
            onSuccess={() => navigate('/documents')}
            onClose={() => navigate('/documents')}
          />
        </div>
      </div>
    </Layout>
  )
}
