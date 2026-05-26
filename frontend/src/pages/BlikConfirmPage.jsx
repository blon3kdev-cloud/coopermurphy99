import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CurrencyAmount } from '../components/CurrencyAmount';
import {
  blikConfirmExchange,
  blikConfirmSession,
  blikConfirmUpload,
} from '../lib/api/blik';
import './BlikConfirmPage.css';

const STEPS = [
  'Wykonaj przelew BLIK na podaną kwotę.',
  'Pobierz oficjalne potwierdzenie z banku (PDF lub wydruk) — nie zrzut ekranu aplikacji.',
  'Prześlij plik dokumentu (PDF, JPG lub PNG) i kliknij „Potwierdź”.',
];

const ERROR_MESSAGES = {
  not_found: 'Nie znaleziono wpłaty. Sprawdź link lub poproś o nowy w bocie.',
  expired: 'Link wygasł. Poproś o nowy link w bocie.',
  proof_required: 'Sesja wygasła. Otwórz ponownie link z wiadomości w bocie.',
  upload_not_allowed: 'Przesyłanie potwierdzenia nie jest już możliwe.',
  invalid_status: 'Ta wpłata nie oczekuje już na potwierdzenie.',
  too_many_attempts: 'Wykorzystano wszystkie próby przesłania.',
  invalid_file_type: 'Dozwolone formaty: PDF, JPG, PNG lub WebP.',
  file_too_large: 'Plik jest za duży (maks. 10 MB).',
  file_content_mismatch: 'Plik nie jest prawidłowym obrazem.',
  screenshot_detected:
    'Odrzucono: wygląda na zrzut ekranu. Prześlij wyłącznie oficjalny dokument z banku (PDF lub skan/wydruk).',
  document_edited:
    'Odrzucono: wykryto możliwą edycję graficzną (np. Photoshop). Prześlij oryginalny, niezmieniony dokument.',
  not_bank_document:
    'Odrzucono: plik nie wygląda na oficjalne potwierdzenie bankowe (brak wymaganych danych BLIK/banku).',
  missing_authenticity_markers:
    'Odrzucono: brak oznak autentyczności (pieczęć, podpis lub identyfikacja banku). Użyj dokumentu z banku.',
  no_text_extracted:
    'Nie udało się odczytać tekstu z dokumentu. Prześlij wyraźniejszy PDF lub zdjęcie wydruku.',
  amount_or_phone_mismatch:
    'Kwota lub numer odbiorcy na dokumencie nie zgadza się z wpłatą.',
  ocr_unavailable:
    'Serwer nie może teraz odczytać zdjęć — prześlij potwierdzenie jako PDF z banku lub skontaktuj się z supportem.',
};

function tokenFromHash() {
  const raw = window.location.hash.replace(/^#/, '').trim();
  return raw || null;
}

function blikErrorMessage(detail, fallback) {
  if (!detail) return fallback;
  const key = typeof detail === 'string' ? detail : detail;
  return ERROR_MESSAGES[key] || (typeof key === 'string' ? key : fallback);
}

function apiErrorMessage(err, fallback) {
  const body = err?.body;
  const detail = body?.error ?? body?.detail ?? err?.message;
  return blikErrorMessage(detail, fallback);
}

export default function BlikConfirmPage() {
  const { token: legacyPathToken } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (legacyPathToken) {
      const hash = legacyPathToken;
      navigate(`/blik/confirm#${encodeURIComponent(hash)}`, { replace: true });
      return undefined;
    }

    let alive = true;

    const load = async () => {
      setLoading(true);
      setError('');
      try {
        const hashToken = tokenFromHash();
        if (hashToken) {
          const data = await blikConfirmExchange(hashToken);
          if (alive) {
            setInfo(data);
            window.history.replaceState(null, '', '/blik/confirm');
          }
          return;
        }
        const data = await blikConfirmSession();
        if (alive) setInfo(data);
      } catch (e) {
        if (alive) setError(apiErrorMessage(e, 'Błąd'));
      } finally {
        if (alive) setLoading(false);
      }
    };

    load();
    return () => {
      alive = false;
    };
  }, [legacyPathToken, navigate]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return undefined;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const pickFile = useCallback((file) => {
    if (!file || !info?.canUpload) return;
    setSelectedFile(file);
    setResult(null);
    setError('');
  }, [info]);

  const onFileInput = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      pickFile(file);
      e.target.value = '';
    },
    [pickFile],
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      pickFile(file);
    },
    [pickFile],
  );

  const onConfirm = useCallback(async () => {
    if (!selectedFile || !info?.canUpload || uploading) return;
    setUploading(true);
    setResult(null);
    setError('');
    try {
      const data = await blikConfirmUpload(selectedFile);
      setResult(data);
      if (data.ok) {
        setInfo((prev) => (prev ? { ...prev, status: 'confirmed', canUpload: false } : prev));
        setSelectedFile(null);
      } else if (data.attemptsLeft > 0) {
        setInfo((prev) => (prev ? { ...prev, canUpload: true } : prev));
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Błąd przesyłania'));
    } finally {
      setUploading(false);
    }
  }, [selectedFile, info, uploading]);

  const clearFile = useCallback(() => {
    setSelectedFile(null);
    setPreviewUrl(null);
  }, []);

  if (loading) {
    return (
      <div className="blik-confirm">
        <div className="blik-confirm__shell">
          <p className="blik-confirm__loading">Ładowanie…</p>
        </div>
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="blik-confirm">
        <div className="blik-confirm__shell blik-confirm__shell--error">
          <h1 className="blik-confirm__title">Potwierdź wpłatę BLIK</h1>
          <p className="blik-confirm__error-msg">{error}</p>
          <p className="blik-confirm__hint">
            Otwórz link z wiadomości w bocie (Discord lub Telegram). Jeśli problem się powtarza,
            poproś o nowy link.
          </p>
        </div>
      </div>
    );
  }

  const confirmed = info?.status === 'confirmed' || result?.ok;
  const canUpload = info?.canUpload && !confirmed;

  return (
    <div className="blik-confirm">
      <div className="blik-confirm__shell">
        <header className="blik-confirm__header">
          <h1 className="blik-confirm__title">Potwierdź wpłatę BLIK</h1>
          <p className="blik-confirm__amount">
            Kwota: <CurrencyAmount value={info?.amountPln} suffix=" zł" />
          </p>
        </header>

        {confirmed ? (
          <div className="blik-confirm__success" role="status">
            <p className="blik-confirm__success-title">Dziękujemy!</p>
            <p>Wpłata została zaksięgowana. Saldo na koncie jest już zaktualizowane.</p>
          </div>
        ) : (
          <>
            <div className="blik-confirm__notice" role="note">
              <strong>Ważne:</strong> akceptujemy wyłącznie{' '}
              <strong>oficjalny dokument</strong> z banku (PDF, wydruk lub zdjęcie wydruku).{' '}
              <strong>Zrzuty ekranu aplikacji są odrzucane</strong> — sprawdzamy metadane, edycję
              graficzną i oznaki banku (logo, pieczęć, podpis).
            </div>

            <ol className="blik-confirm__steps" aria-label="Instrukcja">
              {STEPS.map((text, i) => (
                <li key={text} className="blik-confirm__step">
                  <span className="blik-confirm__step-num" aria-hidden>
                    {i + 1}
                  </span>
                  <span className="blik-confirm__step-text">{text}</span>
                </li>
              ))}
            </ol>

            {canUpload ? (
              <>
                <div
                  className={[
                    'blik-confirm__dropzone',
                    dragOver && 'blik-confirm__dropzone--over',
                    previewUrl && 'blik-confirm__dropzone--has-file',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      fileInputRef.current?.click();
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-label="Wybierz oficjalny dokument potwierdzenia BLIK (nie zrzut ekranu)"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    className="blik-confirm__file-input"
                    onChange={onFileInput}
                  />
                  {previewUrl ? (
                    <img src={previewUrl} alt="" className="blik-confirm__preview" />
                  ) : (
                    <div className="blik-confirm__dropzone-empty">
                      <span className="blik-confirm__dropzone-icon" aria-hidden>
                        ↑
                      </span>
                      <p className="blik-confirm__dropzone-title">
                        Przeciągnij dokument lub kliknij, aby wybrać
                      </p>
                      <p className="blik-confirm__dropzone-meta">
                        PDF, JPG, PNG lub WebP · max 10 MB · bez zrzutów ekranu
                      </p>
                    </div>
                  )}
                </div>

                {selectedFile ? (
                  <button
                    type="button"
                    className="blik-confirm__change-file"
                    onClick={(e) => {
                      e.stopPropagation();
                      clearFile();
                    }}
                  >
                    Wybierz inny plik
                  </button>
                ) : null}

                <button
                  type="button"
                  className="blik-confirm__submit"
                  disabled={!selectedFile || uploading}
                  onClick={onConfirm}
                >
                  {uploading ? 'Przesyłanie…' : 'Potwierdź'}
                </button>
              </>
            ) : (
              <p className="blik-confirm__status">
                Status:{' '}
                {info?.status === 'verifying'
                  ? 'Weryfikacja w toku…'
                  : info?.status === 'proof_rejected'
                    ? 'Odrzucono — skontaktuj się z supportem'
                    : info?.status || '—'}
              </p>
            )}

            {error ? <p className="blik-confirm__error-msg">{error}</p> : null}
            {result && !result.ok ? (
              <p className="blik-confirm__warn">
                {blikErrorMessage(result.reason, 'Nie udało się zweryfikować dokumentu.')}
                {result.attemptsLeft > 0
                  ? ` Pozostało prób: ${result.attemptsLeft}.`
                  : ' Skontaktuj się z supportem.'}
              </p>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
