import React, { useState } from 'react'
import {
  UploadCloud,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { uploadPdfFiles, fetchUploadTaskStatus } from '../services/api'

const STAGE_LABELS = {
  uploading: 'Uploading PDF...',
  parsing: 'Parsing Spatial Bounding Boxes...',
  embedding: 'Computing 384-d Embeddings & Graph Nodes...',
  ready: 'Indexed & Ready',
  failed: 'Ingestion Failed',
}

export default function UploadModal({ isOpen, onClose, onUploadComplete }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [tasks, setTasks] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)

  if (!isOpen) return null

  const handleFilesAdded = (fileList) => {
    setErrorMsg(null)
    const pdfs = Array.from(fileList).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf')
    )
    if (pdfs.length === 0) {
      setErrorMsg('Please select one or more valid .pdf documents.')
      return
    }
    setSelectedFiles((prev) => [...prev, ...pdfs])
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer?.files?.length) {
      handleFilesAdded(e.dataTransfer.files)
    }
  }

  const pollTasksUntilComplete = async (initialTasks) => {
    let activeTasks = [...initialTasks]
    let attempts = 0

    while (attempts < 60) {
      const allDone = activeTasks.every(
        (t) => t.status === 'ready' || t.status === 'failed'
      )
      if (allDone) break

      await new Promise((r) => setTimeout(r, 700))
      attempts += 1

      const updated = await Promise.all(
        activeTasks.map(async (t) => {
          if (t.status === 'ready' || t.status === 'failed') return t
          try {
            return await fetchUploadTaskStatus(t.task_id)
          } catch {
            return t
          }
        })
      )
      activeTasks = updated
      setTasks(updated)
    }

    setIsUploading(false)
    if (onUploadComplete) {
      await onUploadComplete()
    }
  }

  const handleStartUpload = async () => {
    if (selectedFiles.length === 0 || isUploading) return
    setIsUploading(true)
    setErrorMsg(null)

    try {
      const initialTasks = await uploadPdfFiles(selectedFiles)
      setTasks(initialTasks)
      setSelectedFiles([])
      await pollTasksUntilComplete(initialTasks)
    } catch (err) {
      setErrorMsg(err.message || 'Upload failed.')
      setIsUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <UploadCloud className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-bold text-slate-100">
              Ingest Scientific PDFs
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white cursor-pointer p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* Drag-and-Drop Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setIsDragging(true)
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-6 text-center transition ${
              isDragging
                ? 'border-sky-400 bg-sky-500/10'
                : 'border-slate-700 bg-slate-800/40 hover:border-slate-600'
            }`}
          >
            <UploadCloud className="w-9 h-9 text-sky-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-200">
              Drag &amp; drop scientific PDF papers here
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Extracts two-column sections, normalized bounding-box coordinates, 384-d embeddings, and Knowledge Graph entities
            </p>
            <label className="mt-3 inline-block px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-semibold text-sky-300 cursor-pointer transition">
              Browse PDF Files
              <input
                type="file"
                accept=".pdf,application/pdf"
                multiple
                onChange={(e) =>
                  e.target.files?.length && handleFilesAdded(e.target.files)
                }
                className="hidden"
              />
            </label>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Queued Files */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Selected for Ingestion ({selectedFiles.length})
              </p>
              {selectedFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${idx}`}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/70 border border-slate-700 text-xs"
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileText className="w-4 h-4 text-sky-400 shrink-0" />
                    <span className="text-slate-200 truncate">{file.name}</span>
                    <span className="text-slate-500 font-mono">
                      ({(file.size / 1024).toFixed(0)} KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedFiles((prev) => prev.filter((_, i) => i !== idx))
                    }
                    className="text-slate-400 hover:text-rose-400 ml-2 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Staged Progress Indicators (Uploading -> Parsing -> Embedding -> Ready) */}
          {tasks.length > 0 && (
            <div className="space-y-2.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Ingestion Pipeline Status
              </p>
              {tasks.map((task) => {
                const isReady = task.status === 'ready'
                const isFailed = task.status === 'failed'
                return (
                  <div
                    key={task.task_id}
                    className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-slate-200 truncate">
                        {task.filename}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 shrink-0 ${
                          isReady
                            ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            : isFailed
                            ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                            : 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
                        }`}
                      >
                        {isReady ? (
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        ) : isFailed ? (
                          <AlertCircle className="w-3.5 h-3.5" />
                        ) : (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        )}
                        {STAGE_LABELS[task.status] || task.status}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1.5 rounded-full bg-slate-950 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          isReady
                            ? 'bg-emerald-400'
                            : isFailed
                            ? 'bg-rose-500'
                            : 'bg-sky-400'
                        }`}
                        style={{ width: `${task.progress_percentage || 25}%` }}
                      />
                    </div>

                    {task.error_message && (
                      <p className="text-[11px] text-rose-300">
                        {task.error_message}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/90 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 transition cursor-pointer"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleStartUpload}
            disabled={selectedFiles.length === 0 || isUploading}
            className="px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-500 text-slate-950 text-xs font-bold flex items-center gap-1.5 transition cursor-pointer"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Ingesting...
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                Start Ingestion ({selectedFiles.length})
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

