import { type FormEvent, useState } from 'react'

const API_URL = import.meta.env?.VITE_API_URL

const QUESTION_MAX_LENGTH = 256;

function App() {
  const [prompt, setPrompt] = useState('')
  const [lastQuestion, setLastQuestion] = useState<string | null>(null)
  const [answer, setAnswer] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onAsk = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmedPrompt = prompt.trim()
    if (!trimmedPrompt || isLoading) {
      return
    }
    if (trimmedPrompt.length > QUESTION_MAX_LENGTH) {
      setError(`The question cannot exceed ${QUESTION_MAX_LENGTH}`)
      return;
    }

    try {
      setIsLoading(true)
      setError(null)
      setLastQuestion(trimmedPrompt)
      setAnswer(null)

      const response = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', },
        body: JSON.stringify({ question: trimmedPrompt }),
      })

      if (!response.ok) {
        const { message } = await response.json()
        throw new Error(message || `There's been an error processing the request`)
      }

      const data: { answer?: string } = await response.json()
      setAnswer(data.answer ?? 'No answer returned from the API.')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong while contacting the API.',
      )
    } finally {
      setIsLoading(false)
      setPrompt('')
    }
  }

  if (!API_URL) {
    return <p className='text-white'>API_URL is not set</p>
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
            Dynamic RAG
          </p>
          <h1 className="mt-2 text-4xl font-semibold text-white">
            Ask anything about your data
          </h1>
          <p className="mt-2 text-base text-slate-400">
            We'll use the uploaded documents to generate a response
          </p>
        </header>

        <section className="flex-1 rounded-3xl border border-slate-800 bg-slate-900/60 shadow-2xl shadow-slate-900/50 backdrop-blur">
          <div className="border-b border-slate-800 px-6 py-5">
            <form onSubmit={onAsk} className="flex flex-col gap-4 md:flex-row">
              <label htmlFor="prompt" className="sr-only">
                Your question
              </label>
              <input
                id="prompt"
                name="prompt"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="E.g. What does the knowledge base say about onboarding?"
                className="flex-1 rounded-2xl border border-slate-800 bg-slate-900/70 px-5 py-4 text-base text-white outline-none ring-2 ring-transparent transition focus:ring-cyan-400 focus-visible:ring-cyan-400"
                disabled={isLoading}
                autoComplete="off"
              />
              <button
                type="submit"
                className="rounded-2xl bg-cyan-400 px-8 py-4 text-base font-semibold text-slate-900 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
                disabled={!prompt.trim() || isLoading}
              >
                {isLoading ? 'Thinking...' : 'Ask'}
              </button>
            </form>
            {error && (
              <p className="mt-3 text-sm text-rose-300">{error}</p>
            )}
          </div>

          <div className="px-6 py-8">
            {lastQuestion ? (
              <div className="space-y-6">
                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-slate-500">
                    You asked
                  </p>
                  <p className="mt-2 text-lg text-white">{lastQuestion}</p>
                </div>

                <div>
                  <p className="text-sm uppercase tracking-[0.3em] text-slate-500">
                    Answer
                  </p>
                  <div className="mt-2 rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-base text-slate-100">
                    {answer ?? 'Waiting for the model response...'}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
                <p>Ask your first question to see the answer show up here.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
