import { useState, useRef, useEffect } from 'react'
import JobCard from './JobCard';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function App() {
  const [messages, setMessages] = useState<{role: 'user' | 'agent', content: string, jobs?: any[]}[]>([
    { role: 'agent', content: "Hello! I'm your local AI Job Hunt Agent. How can I help you find your next role today? You can ask me to search LinkedIn or upload your resume!" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [resumeName, setResumeName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const userMsg = { role: 'user' as const, content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Use 127.0.0.1 instead of localhost to avoid Windows IPv6 mapping issues
      const res = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg.content })
      });
      
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'agent', content: data.reply || "Error: No response from agent.", jobs: data.jobs || [] }]);
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'agent', content: `Error communicating with backend: ${err.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file.');
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/upload_resume', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setResumeName(file.name);
        setMessages(prev => [...prev, { role: 'agent', content: `I have successfully parsed your resume (${file.name}). I will use it to find better job matches for you!` }]);
      } else {
        alert(`Upload failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (err) {
      alert('Error connecting to backend for upload.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-50 font-sans">
      {/* Sidebar / Settings Panel */}
      <aside className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col hidden md:flex">
        <div className="p-4 border-b border-slate-700">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">JobHunt AI</h1>
          <p className="text-xs text-slate-400 mt-1">Local & Private Job Search</p>
        </div>
        <div className="p-4 flex-1">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Configured Model</label>
              <div className="w-full bg-slate-900 border border-slate-700 rounded-md p-2 text-sm text-slate-300">
                Loaded from .env config
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Resume (Context)</label>
              <input 
                type="file" 
                accept="application/pdf" 
                className="hidden" 
                ref={fileInputRef} 
                onChange={handleFileUpload} 
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full bg-slate-700 hover:bg-slate-600 disabled:opacity-50 transition-colors border border-slate-600 rounded-md p-2 text-sm text-left flex items-center justify-between"
              >
                <span className="truncate">{isUploading ? 'Uploading...' : (resumeName || 'Upload PDF...')}</span>
                <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-2xl rounded-2xl px-5 py-3 ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-200 shadow-sm border border-slate-700'}`}>
                {msg.role === 'user' ? (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                ) : (
                  <div className="prose prose-invert prose-sm md:prose-base max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-a:text-blue-400 hover:prose-a:text-blue-300">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
              
              {/* Render Job Cards if they exist for this agent message */}
              {msg.role === 'agent' && msg.jobs && msg.jobs.length > 0 && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-4xl">
                  {msg.jobs.map((job, jIdx) => (
                    <JobCard key={jIdx} job={job} />
                  ))}
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-2xl rounded-2xl px-5 py-3 bg-slate-800 text-slate-400 border border-slate-700 flex space-x-2 items-center">
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-slate-900 border-t border-slate-800">
          <div className="max-w-3xl mx-auto relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="e.g. Find remote React developer jobs with no experience required..."
              className="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-full pl-5 pr-12 py-3 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all shadow-inner"
            />
            <button 
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="absolute right-2 p-2 bg-blue-600 text-white rounded-full hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
