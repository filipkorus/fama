import { useParams } from 'react-router-dom'
import ChatComponent from '../components/Chat'

export default function ChatPage() {
  const { contactId } = useParams<{ contactId?: string }>()

  return (
    <div className="page">
      <ChatComponent to={contactId || null} />
    </div>
  );
}