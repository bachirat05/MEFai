import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  ChangeEvent,
  DragEvent,
} from "react";

import type { User } from "firebase/auth";

import {
  AlertCircle,
  CheckCircle2,
  FileText,
  FolderOpen,
  LoaderCircle,
  Trash2,
  Upload,
  UploadCloud,
} from "lucide-react";

import {
  deleteDocument,
  getDocuments,
  type DeleteDocumentResponse,
  type RagDocument,
  type UploadDocumentResponse,
  uploadDocument,
} from "../../services/api";

import {
  EmptyState,
  PageHeader,
  SectionCard,
  StatCard,
} from "../ui";


type DocumentsPageProps = {
  user: User;
};


function formatFileSize(
  size: number
): string {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(
      size / 1024
    ).toFixed(1)} KB`;
  }

  return `${(
    size /
    (1024 * 1024)
  ).toFixed(1)} MB`;
}


function DocumentsPage({
  user,
}: DocumentsPageProps) {
  const fileInputRef =
    useRef<HTMLInputElement | null>(null);

  const [documents, setDocuments] =
    useState<RagDocument[]>([]);

  const [isLoading, setIsLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [isUploading, setIsUploading] =
    useState(false);

  const [uploadError, setUploadError] =
    useState<string | null>(null);

  const [uploadSuccess, setUploadSuccess] =
    useState<UploadDocumentResponse | null>(null);

  const [deletingDocument, setDeletingDocument] =
    useState<string | null>(null);

  const [deleteError, setDeleteError] =
    useState<string | null>(null);

  const [deleteSuccess, setDeleteSuccess] =
    useState<DeleteDocumentResponse | null>(null);

  const [isDragging, setIsDragging] =
    useState(false);


  const loadDocuments = useCallback(
    async (): Promise<void> => {
      try {
        setIsLoading(true);
        setError(null);

        const token =
          await user.getIdToken();

        const result =
          await getDocuments(
            token
          );

        setDocuments(result);
      } catch (err) {
        console.error(
          "Documents loading error:",
          err
        );

        setError(
          err instanceof Error
            ? err.message
            : "Impossible de charger les documents."
        );
      } finally {
        setIsLoading(false);
      }
    },
    [user]
  );


  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);


  function handleSelectFile(
    event: ChangeEvent<HTMLInputElement>
  ): void {
    const file =
      event.target.files?.[0] ?? null;

    setSelectedFile(file);
    setUploadError(null);
    setUploadSuccess(null);
  }

  function handleDrop(
    event: DragEvent<HTMLDivElement>
  ): void {
    event.preventDefault();
    setIsDragging(false);

    const file =
      event.dataTransfer.files?.[0] ?? null;

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setUploadError(null);
    setUploadSuccess(null);
    setDeleteError(null);
    setDeleteSuccess(null);
  }


  async function handleUpload(): Promise<void> {
    if (
      selectedFile === null
      || isUploading
    ) {
      return;
    }

    try {
      setIsUploading(true);
      setUploadError(null);
      setUploadSuccess(null);

      const token =
        await user.getIdToken();

      const result =
        await uploadDocument(
          token,
          selectedFile
        );

      setUploadSuccess(result);
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadDocuments();
    } catch (err) {
      console.error(
        "Document upload error:",
        err
      );

      setUploadError(
        err instanceof Error
          ? err.message
          : "Impossible d'ajouter le document."
      );
    } finally {
      setIsUploading(false);
    }
  }


  async function handleDelete(
    document: RagDocument
  ): Promise<void> {
    if (deletingDocument !== null) {
      return;
    }

    const confirmed = window.confirm(
      `Supprimer le document "${document.name}" ?\n\nSes chunks seront aussi supprimes du RAG.`
    );

    if (!confirmed) {
      return;
    }

    try {
      setDeletingDocument(document.name);
      setDeleteError(null);
      setDeleteSuccess(null);
      setUploadError(null);
      setUploadSuccess(null);

      const token =
        await user.getIdToken();

      const result =
        await deleteDocument(
          token,
          document.name
        );

      setDeleteSuccess(result);

      await loadDocuments();
    } catch (err) {
      console.error(
        "Document deletion error:",
        err
      );

      setDeleteError(
        err instanceof Error
          ? err.message
          : "Impossible de supprimer le document."
      );
    } finally {
      setDeletingDocument(null);
    }
  }


  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="mx-auto max-w-6xl">
        <PageHeader
          title="Documents"
          description="Administrez les fichiers utilises par le systeme RAG."
          icon={FolderOpen}
          eyebrow="Base documentaire"
          action={
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-violet-300"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
            >
              <Upload size={17} />
              Ajouter un document
            </button>
          }
        />

        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <StatCard
            label="Documents disponibles"
            value={isLoading ? "..." : documents.length}
            icon={FolderOpen}
            tone="violet"
          />
          <StatCard
            label="Formats supportes"
            value="TXT, PDF, DOCX"
            icon={FileText}
            tone="blue"
          />
          <StatCard
            label="Ingestion RAG"
            value="Active"
            icon={Upload}
            tone="emerald"
          />
        </div>

        <SectionCard
          title="Ajouter un document"
          description="Ajoutez un fichier TXT, PDF ou DOCX a la base RAG."
          icon={UploadCloud}
          className="mb-8"
        >
          <div className="space-y-4">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf,.docx"
              className="hidden"
              onChange={handleSelectFile}
            />

            <div
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`rounded-2xl border border-dashed p-5 transition ${
                isDragging
                  ? "border-violet-300 bg-violet-50"
                  : "border-slate-300 bg-slate-50"
              }`}
            >
              {selectedFile ? (
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white text-violet-600 shadow-sm">
                    <FileText size={18} />
                  </div>

                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-800">
                      {selectedFile.name}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {formatFileSize(
                        selectedFile.size
                      )}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                  onClick={() => void handleUpload()}
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <LoaderCircle
                      size={17}
                      className="animate-spin"
                    />
                  ) : (
                    <Upload size={17} />
                  )}
                  Indexer
                </button>
              </div>
              ) : (
              <div className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-violet-600 shadow-sm">
                  <UploadCloud size={22} />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-700">
                  Deposez un fichier ici
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  ou utilisez le bouton Ajouter un document.
                </p>
              </div>
              )}
            </div>

            {uploadSuccess ? (
              <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <CheckCircle2
                  size={18}
                  className="mt-0.5 shrink-0"
                />

                <div>
                  <p className="font-semibold">
                    {uploadSuccess.message}
                  </p>

                  <p className="mt-1">
                    {uploadSuccess.name} - {uploadSuccess.type.toUpperCase()} -
                    {" "}
                    {formatFileSize(uploadSuccess.size)} -
                    {" "}
                    {uploadSuccess.chunks} chunks indexes
                  </p>
                </div>
              </div>
            ) : null}

            {uploadError ? (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle
                  size={18}
                  className="mt-0.5 shrink-0"
                />

                <p>
                  {uploadError}
                </p>
              </div>
            ) : null}

            {deleteSuccess ? (
              <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                <CheckCircle2
                  size={18}
                  className="mt-0.5 shrink-0"
                />

                <div>
                  <p className="font-semibold">
                    {deleteSuccess.message}
                  </p>

                  <p className="mt-1">
                    {deleteSuccess.name} - {deleteSuccess.chunks_deleted}
                    {" "}
                    chunk(s) supprime(s) du RAG
                  </p>
                </div>
              </div>
            ) : null}

            {deleteError ? (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertCircle
                  size={18}
                  className="mt-0.5 shrink-0"
                />

                <p>
                  {deleteError}
                </p>
              </div>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard
          title="Base documentaire"
          description="Documents disponibles pour l'assistant RH."
          icon={FileText}
        >

          {isLoading ? (

            <div className="p-8 text-center text-sm text-slate-500">
              Chargement des documents...
            </div>

          ) : error ? (

            <div className="p-8 text-center text-sm text-red-600">
              {error}
            </div>

          ) : documents.length === 0 ? (

            <EmptyState
              icon={FileText}
              title="Aucun document"
              description="Ajoutez un document pour alimenter la recherche RAG."
            />

          ) : (

            <div className="divide-y divide-slate-100">

              {documents.map(
                (document) => (
                  <div
                    key={document.name}
                    className="flex items-center justify-between gap-4 px-6 py-4"
                  >
                    <div className="flex min-w-0 items-center gap-4">

                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600">
                        <FileText size={19} />
                      </div>

                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-slate-800">
                          {document.name}
                        </p>

                        <p className="mt-1 text-xs text-slate-400">
                          {formatFileSize(
                            document.size
                          )}
                        </p>
                      </div>

                    </div>

                    <div className="flex shrink-0 items-center gap-3">
                      <span className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold uppercase text-slate-600">
                        {document.type}
                      </span>

                      <button
                        type="button"
                        className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-100 text-red-500 transition hover:border-red-200 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                        title={`Supprimer ${document.name}`}
                        aria-label={`Supprimer ${document.name}`}
                        onClick={() => void handleDelete(document)}
                        disabled={deletingDocument !== null}
                      >
                        {deletingDocument === document.name ? (
                          <LoaderCircle
                            size={16}
                            className="animate-spin"
                          />
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                    </div>
                  </div>
                )
              )}

            </div>

          )}

        </SectionCard>

      </div>
    </div>
  );
}


export default DocumentsPage;
