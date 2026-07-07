import { create } from 'zustand'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface Thread {
  id: string
  title: string
  messages: Message[]
  lastModified: number
}

interface AppState {
  threads: Thread[]
  currentThreadId: string | null
  selectedDocuments: string[]
  
  // Actions
  toggleDocumentSelection: (docName: string) => void
  createThread: () => Promise<string>
  loadThreads: () => Promise<void>
  selectThread: (threadId: string) => void
  addMessage: (threadId: string, message: Omit<Message, 'id' | 'timestamp'>) => void
  updateLastMessage: (threadId: string, content: string) => void
  deleteThread: (threadId: string) => void
}

// Mock initial data
const INITIAL_THREAD_ID = 'default-thread'
const INITIAL_THREAD: Thread = {
    id: INITIAL_THREAD_ID,
    title: 'New Chat',
    messages: [],
    lastModified: Date.now()
}

export const useAppStore = create<AppState>((set, get) => ({
  threads: [INITIAL_THREAD],
  currentThreadId: INITIAL_THREAD_ID,
  selectedDocuments: [],

  toggleDocumentSelection: (docName: string) => {
    set(state => {
      if (state.selectedDocuments.includes(docName)) {
        return { selectedDocuments: state.selectedDocuments.filter(d => d !== docName) }
      } else {
        return { selectedDocuments: [...state.selectedDocuments, docName] }
      }
    })
  },

  createThread: async () => {
    const newThread: Thread = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      lastModified: Date.now()
    }
    set(state => ({
      threads: [newThread, ...state.threads],
      currentThreadId: newThread.id
    }))
    return newThread.id
  },

  loadThreads: async () => {
    // In a real app, fetch from backend here
    // For now we use local state or localStorage
  },

  selectThread: (threadId: string) => {
    set({ currentThreadId: threadId })
  },

  addMessage: (threadId: string, msg) => {
    set(state => {
      const threadIndex = state.threads.findIndex(t => t.id === threadId)
      if (threadIndex === -1) return state

      const newMsg: Message = {
        ...msg,
        id: crypto.randomUUID(),
        timestamp: new Date().toISOString()
      }

      const updatedThreads = [...state.threads]
      updatedThreads[threadIndex] = {
        ...updatedThreads[threadIndex],
        messages: [...updatedThreads[threadIndex].messages, newMsg],
        lastModified: Date.now()
      }
      
      // Update title if it's the first user message
      if (msg.role === 'user' && updatedThreads[threadIndex].messages.length === 1) {
          updatedThreads[threadIndex].title = msg.content.slice(0, 30)
      }

      return { threads: updatedThreads }
    })
  },
  
  updateLastMessage: (threadId: string, content: string) => {
       set(state => {
      const threadIndex = state.threads.findIndex(t => t.id === threadId)
      if (threadIndex === -1) return state
      
      const thread = state.threads[threadIndex]
      if (thread.messages.length === 0) return state
      
      const lastMsgIndex = thread.messages.length - 1
      const updatedThreads = [...state.threads]
      
      const updatedMsgs = [...thread.messages]
      updatedMsgs[lastMsgIndex] = {
          ...updatedMsgs[lastMsgIndex],
          content: content
      }
      
      updatedThreads[threadIndex] = {
          ...thread,
          messages: updatedMsgs
      }
      
      return { threads: updatedThreads }
    })
  },

  deleteThread: (threadId: string) => {
    set(state => ({
      threads: state.threads.filter(t => t.id !== threadId),
      currentThreadId: state.currentThreadId === threadId ? null : state.currentThreadId
    }))
  }
}))
