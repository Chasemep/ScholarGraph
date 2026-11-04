import React, { useState } from 'react'
import {
  UploadCloud,
  X,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { uploadPdfFiles, fetchUploadTaskStatus } from '../../services/api'

const STAGE_LABELS = {
  uploading: 'Uploading PDF...',
  parsing: 'Reading pages and text...',
  embedding: 'Indexing paper and citations...',
  ready: 'Indexed & Added',
  failed: 'Upload failed',
}

export default function UploadModal({ isOpen, onClose, onUploadComplete }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [tasks, setTasks] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [errorMsg, setErrorMsg] = useState(null)

  if (!isOpen) return null

  const allTasksFinished =
    tasks.length > 0 &&
    !isUploading &&
    tasks.every((t) => t.status === 'ready' || t.status === 'failed')
  const readyCount = tasks.filter((t) => t.status === 'ready').length

  const handleCloseModal = () => {
    if (!isUploading) {
      setTasks([])
      setSelectedFiles([])
      setErrorMsg(null)
    }
    onClose()
  }

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

    while (attempts < 300) {
      const allDone = activeTasks.every(
        (t) => t.status === 'ready' || t.status === 'failed'
      )
      if (allDone) break

      await new Promise((r) => setTimeout(r, 1000))
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
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg rounded-xl bg-[#18181b] border border-[#27272a] shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-[#27272a] bg-[#09090b]/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-[#6366f1]" />
            <h3 className="text-sm font-semibold text-[#f4f4f5]">
              Upload PDF Papers
            </h3>
          </div>
          <button
            type="button"
            onClick={handleCloseModal}
            className="text-[#a1a1aa] hover:text-[#f4f4f5] cursor-pointer p-1"
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
            className={`border border-dashed rounded-xl p-6 text-center transition ${
              isDragging
                ? 'border-[#6366f1] bg-[#6366f1]/10'
                : 'border-[#27272a] bg-[#09090b]/60 hover:border-[#6366f1]/50'
            }`}
          >
            <UploadCloud className="w-8 h-8 text-[#6366f1] mx-auto mb-2" />
            <p className="text-xs font-medium text-[#f4f4f5]">
              Drag &amp; drop PDF papers here
            </p>
            <p className="text-[11px] text-[#a1a1aa] mt-1">
              Uploaded papers will be indexed for search, citations, and the knowledge graph
            </p>
            <label className="mt-3 inline-block px-3.5 py-1.5 rounded-md bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-xs font-medium text-[#f4f4f5] cursor-pointer transition">
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
              <p className="text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                Selected Files ({selectedFiles.length})
              </p>
              {selectedFiles.map((file, idx) => (
                <div
                  key={`${file.name}-${idx}`}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#09090b] border border-[#27272a] text-xs"
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileText className="w-3.5 h-3.5 text-[#6366f1] shrink-0" />
                    <span className="text-[#f4f4f5] truncate">{file.name}</span>
                    <span className="text-[#a1a1aa] font-mono text-[11px]">
                      ({(file.size / 1024).toFixed(0)} KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedFiles((prev) => prev.filter((_, i) => i !== idx))
                    }
                    className="text-[#a1a1aa] hover:text-rose-400 ml-2 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Staged Progress Indicators */}
          {tasks.length > 0 && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[#a1a1aa]">
                  {allTasksFinished ? 'Completed Uploads' : 'Upload Progress'}
                </p>
                {allTasksFinished && readyCount > 0 && (
                  <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Added {readyCount} {readyCount === 1 ? 'paper' : 'papers'} to graph
                  </span>
                )}
              </div>
              {tasks.map((task) => {
                const isReady = task.status === 'ready'
                const isFailed = task.status === 'failed'
                return (
                  <div
                    key={task.task_id}
                    className="p-3 rounded-lg bg-[#09090b] border border-[#27272a] space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-medium text-[#f4f4f5] truncate">
                        {task.filename}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-medium flex items-center gap-1 shrink-0 ${
                          isReady
                            ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                            : isFailed
                            ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                            : 'bg-[#6366f1]/15 text-[#818cf8] border border-[#6366f1]/30'
                        }`}
                      >
                        {isReady ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : isFailed ? (
                          <AlertCircle className="w-3 h-3" />
                        ) : (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        )}
                        {STAGE_LABELS[task.status] || task.status}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full h-1 rounded-full bg-[#18181b] overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          isReady
                            ? 'bg-emerald-400'
                            : isFailed
                            ? 'bg-rose-500'
                            : 'bg-[#6366f1]'
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
        <div className="px-5 py-3 border-t border-[#27272a] bg-[#09090b]/50 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleCloseModal}
            className="px-3 py-1.5 rounded-md bg-[#09090b] hover:bg-[#27272a] border border-[#27272a] text-xs font-medium text-[#a1a1aa] hover:text-[#f4f4f5] transition cursor-pointer"
          >
            {allTasksFinished && selectedFiles.length === 0 ? 'Cancel' : 'Close'}
          </button>

          {allTasksFinished && selectedFiles.length === 0 ? (
            <button
              type="button"
              onClick={handleCloseModal}
              className="px-4 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Done ({readyCount} Indexed)
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStartUpload}
              disabled={selectedFiles.length === 0 || isUploading}
              className="px-3.5 py-1.5 rounded-md bg-[#6366f1] hover:bg-[#4f46e5] disabled:bg-[#09090b] disabled:text-[#a1a1aa]/40 disabled:border disabled:border-[#27272a] text-white text-xs font-medium flex items-center gap-1.5 transition cursor-pointer"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" />
                  Upload ({selectedFiles.length})
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
