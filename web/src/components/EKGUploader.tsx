"use client";

import { useCallback, useRef, useState } from "react";
import type { AnalyzeRequest } from "@/types/analysis";

interface EKGUploaderProps {
  onAnalyzing: () => void;
  onResult: (result: unknown) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
type AcceptedMediaType = (typeof ACCEPTED_TYPES)[number];

function isAcceptedType(type: string): type is AcceptedMediaType {
  return ACCEPTED_TYPES.includes(type as AcceptedMediaType);
}

export default function EKGUploader({
  onAnalyzing,
  onResult,
  onError,
  disabled,
}: EKGUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const processFile = useCallback(
    async (file: File) => {
      if (!isAcceptedType(file.type)) {
        onError("Please upload a JPEG, PNG, or WebP image.");
        return;
      }

      const reader = new FileReader();
      reader.onload = async (e) => {
        const dataUrl = e.target?.result as string;
        setPreview(dataUrl);

        // Strip the data URL prefix to get raw base64
        const base64 = dataUrl.split(",")[1];

        const body: AnalyzeRequest = {
          imageBase64: base64,
          mediaType: file.type as AcceptedMediaType,
        };

        onAnalyzing();
        try {
          const res = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const data = await res.json();
          if (data.success) {
            onResult(data.result);
          } else {
            onError(data.error ?? "Analysis failed");
          }
        } catch (err) {
          onError(err instanceof Error ? err.message : "Network error");
        }
      };
      reader.readAsDataURL(file);
    },
    [onAnalyzing, onResult, onError]
  );

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

  return (
    <div className="flex flex-col items-center gap-4">
      <div
        className={`w-full max-w-2xl border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
          ${dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"}
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={!disabled ? handleDrop : undefined}
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
          <img
            src={preview}
            alt="EKG preview"
            className="mx-auto max-h-64 object-contain rounded-lg"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            <p className="text-lg font-medium">Drop EKG image here</p>
            <p className="text-sm">or click to browse — JPEG, PNG, WebP</p>
          </div>
        )}
      </div>

      {preview && !disabled && (
        <button
          className="text-sm text-gray-500 underline hover:text-gray-700"
          onClick={() => {
            setPreview(null);
            if (inputRef.current) inputRef.current.value = "";
          }}
        >
          Clear image
        </button>
      )}
    </div>
  );
}
