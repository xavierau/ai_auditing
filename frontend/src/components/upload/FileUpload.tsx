/**
 * FileUpload Component
 *
 * Secure drag-drop file upload with validation.
 * Follows design system file upload zone pattern.
 */

import { useState, useRef, useCallback } from 'react';
import { Upload, AlertCircle, CheckCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { SanitizerService } from '@/services/sanitizer';

export interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number; // in bytes
  className?: string;
  disabled?: boolean;
}

/**
 * File validation result
 */
interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Default configuration
 */
const DEFAULT_ACCEPT = '.xlsx';
const DEFAULT_MAX_SIZE = 50 * 1024 * 1024; // 50MB

/**
 * FileUpload - Drag-drop file upload with validation
 *
 * @example
 * <FileUpload
 *   onFileSelect={(file) => handleUpload(file)}
 *   accept=".xlsx"
 *   maxSize={50 * 1024 * 1024}
 * />
 */
export function FileUpload({
  onFileSelect,
  accept = DEFAULT_ACCEPT,
  maxSize = DEFAULT_MAX_SIZE,
  className,
  disabled = false,
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Validate file
   */
  const validateFile = useCallback(
    (file: File): ValidationResult => {
      // Check file size
      if (file.size > maxSize) {
        return {
          valid: false,
          error: `File size exceeds ${Math.round(maxSize / 1024 / 1024)}MB limit`,
        };
      }

      // Check file type
      if (accept) {
        const acceptedTypes = accept.split(',').map((t) => t.trim());
        const fileExt = `.${file.name.split('.').pop()?.toLowerCase()}`;
        if (!acceptedTypes.includes(fileExt)) {
          return {
            valid: false,
            error: `File type not accepted. Accepted types: ${accept}`,
          };
        }
      }

      // Sanitize filename
      const sanitizedName = SanitizerService.sanitizeFilename(file.name);
      if (sanitizedName !== file.name) {
        console.warn('Filename was sanitized:', file.name, '->', sanitizedName);
      }

      return { valid: true };
    },
    [accept, maxSize]
  );

  /**
   * Handle file selection
   */
  const handleFileSelect = useCallback(
    (file: File) => {
      const validation = validateFile(file);

      if (!validation.valid) {
        setError(validation.error || 'Invalid file');
        setSelectedFile(null);
        return;
      }

      setError(null);
      setSelectedFile(file);
      onFileSelect(file);
    },
    [validateFile, onFileSelect]
  );

  /**
   * Handle drag events
   */
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (disabled) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [disabled, handleFileSelect]
  );

  /**
   * Handle file input change
   */
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
  );

  /**
   * Open file dialog
   */
  const openFileDialog = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [disabled]);

  /**
   * Clear selection
   */
  const clearSelection = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  return (
    <div className={cn('w-full', className)}>
      {/* Upload Zone */}
      <div
        className={cn(
          'relative flex flex-col items-center justify-center rounded-lg',
          'border-2 border-dashed p-12 transition-all',
          isDragOver
            ? 'border-blue-500 bg-blue-50'
            : error
            ? 'border-red-300 bg-red-50'
            : selectedFile
            ? 'border-green-300 bg-green-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100',
          disabled && 'cursor-not-allowed opacity-60'
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* Icon */}
        <div className="mb-4">
          {error ? (
            <AlertCircle className="h-12 w-12 text-red-500" aria-hidden="true" />
          ) : selectedFile ? (
            <CheckCircle className="h-12 w-12 text-green-500" aria-hidden="true" />
          ) : (
            <Upload
              className={cn(
                'h-12 w-12',
                isDragOver ? 'text-blue-500' : 'text-gray-400'
              )}
              aria-hidden="true"
            />
          )}
        </div>

        {/* Text */}
        <div className="text-center">
          {error ? (
            <p className="text-sm font-medium text-red-700">{error}</p>
          ) : selectedFile ? (
            <>
              <p className="text-sm font-medium text-green-700">File selected</p>
              <p className="mt-1 text-xs text-gray-600">{selectedFile.name}</p>
              <p className="text-xs text-gray-500">
                ({Math.round(selectedFile.size / 1024)} KB)
              </p>
            </>
          ) : isDragOver ? (
            <p className="text-sm font-medium text-blue-700">Drop file here</p>
          ) : (
            <>
              <p className="text-sm font-medium text-gray-700">
                Drag and drop file here
              </p>
              <p className="mt-1 text-xs text-gray-500">or</p>
            </>
          )}
        </div>

        {/* Buttons */}
        {!selectedFile && !error && (
          <Button
            type="button"
            onClick={openFileDialog}
            disabled={disabled}
            className="mt-4"
            aria-label="Select file"
          >
            Select File
          </Button>
        )}

        {selectedFile && (
          <Button
            type="button"
            onClick={clearSelection}
            variant="outline"
            className="mt-4"
            aria-label="Clear selection"
          >
            <X className="mr-2 h-4 w-4" />
            Clear
          </Button>
        )}

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="sr-only"
          disabled={disabled}
          aria-label="File input"
        />
      </div>

      {/* File requirements */}
      <p className="mt-2 text-xs text-gray-500">
        Accepted file types: {accept} • Maximum size:{' '}
        {Math.round(maxSize / 1024 / 1024)}MB
      </p>
    </div>
  );
}
