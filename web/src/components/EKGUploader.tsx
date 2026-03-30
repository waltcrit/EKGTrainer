"use client";

import { useCallback, useRef, useState } from "react";
import type { AnalyzeRequest } from "@/types/analysis";

interface EKGUploaderProps {
  onAnalyzing: () => void;
  onResult:    (result: unknown) => void;
  onError:     (error: string)   => void;
  disabled?:   boolean;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
type AcceptedMediaType = (typeof ACCEPTED_TYPES)[number];

function isAcceptedType(type: string): type is AcceptedMediaType {
  return ACCEPTED_TYPES.includes(type as AcceptedMediaType);
}

export default function EKGUploader({ onAnalyzing, onResult, onError, disabled }: EKGUploaderProps) {
  const inputRef              = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const processFile = useCallback(async (file: File) => {
    if (!isAcceptedType(file.type)) {
      onError("Please upload a JPEG, PNG, or WebP image.");
      return;
    }

    const reader = new FileReader();
    reader.onload = async (e) => {
      const dataUrl = e.target?.result as string;
      setPreview(dataUrl);
      const base64 = dataUrl.split(",")[1];
      const body: AnalyzeRequest = { imageBase64: base64, mediaType: file.type as AcceptedMediaType };
      onAnalyzing();
      try {
        const res  = await fetch("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        const data = await res.json();
        if (data.success) onResult(data.result);
        else              onError(data.error ?? "Analysis failed");
      } catch (err) {
        onError(err instanceof Error ? err.message : "Network error");
      }
    };
    reader.readAsDataURL(file);
  }, [onAnalyzing, onResult, onError]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleClear = () => {
    setPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={!disabled ? handleDrop : undefined}
        className={[
          "relative w-full rounded-xl border-2 border-dashed transition-all duration-150 cursor-pointer overflow-hidden",
          dragging
            ? "border-sky-400 bg-sky-50"
            : "border-slate-200 bg-white hover:border-sky-300 hover:bg-slate-50",
          disabled ? "opacity-50 cursor-not-allowed" : "",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleFileChange}
          disabled={disabled}
        />

        {preview ? (
          /* Preview */
          <div className="bg-[#fff5e6]">
            <img src={preview} alt="EKG preview" className="w-full max-h-72 object-contain" />
            <div className="px-3 py-1 border-t border-[#ffe4b8]">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700/50">
                EKG Image Preview
              </span>
            </div>
          </div>
        ) : (
          /* Drop zone */
          <div className="flex flex-col items-center justify-center gap-3 py-14 px-6 text-center">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
              dragging ? "bg-sky-100" : "bg-slate-100"
            }`}>
              <svg className={`w-6 h-6 transition-colors ${dragging ? "text-sky-500" : "text-slate-400"}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-700">
                {dragging ? "Drop to analyze" : "Drop an EKG image here"}
              </p>
              <p className="text-xs text-slate-400 mt-1">or click to browse — JPEG, PNG, WebP</p>
            </div>
          </div>
        )}
      </div>

      {preview && !disabled && (
        <button
          onClick={handleClear}
          className="self-center text-xs text-slate-400 hover:text-slate-600 transition-colors
                     underline underline-offset-2"
        >
          Clear image
        </button>
      )}
    </div>
  );
}
