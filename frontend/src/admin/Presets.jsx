import React, { useMemo, useRef, useState } from 'react';
import AdminContentLoader from './AdminContentLoader';
import { Card, DataTable, Field, Icon, Modal, Page, Toolbar } from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';
import { safeImageUrl, safePreviewImageUrl } from '../lib/safeUrl';
import '../components/featured-bets/FeaturedBets.css';

function presetAppliedAlert(result, { isUpdate = false } = {}) {
  const n = result?.appliedCount ?? 0;
  const titles = (result.appliedTo ?? []).map((m) => m.title).filter(Boolean);
  const preview = titles.slice(0, 3).join(', ');
  const more = titles.length > 3 ? ` (+${titles.length - 3})` : '';
  if (n <= 0) {
    window.alert(
      isUpdate
        ? 'Preset saved, but no active bets matched its codes. Check that bet titles or Yes/No labels include a preset code.'
        : 'Preset saved. No open active bets without an image matched its codes yet.',
    );
    return;
  }
  window.alert(
    `Preset saved. Image set for ${n} active bet${n === 1 ? '' : 's'}${preview ? `: ${preview}${more}` : ''}. Refresh the Bets page if it is already open.`,
  );
}

const COLS = [
  {
    key: 'image',
    label: '',
    width: 56,
    render: (r) => {
      const src = safeImageUrl(r.imageUrl);
      return src ? (
        <img src={src} alt="" className="ad-thumb" />
      ) : (
        <span className="ad-thumb ad-thumb--empty" aria-hidden="true" />
      );
    },
  },
  {
    key: 'names',
    label: 'Codes',
    render: (r) => (
      <div className="ad-tags-row">
        {r.names.map((n) => (
          <span key={n} className="ad-tag">{n}</span>
        ))}
      </div>
    ),
  },
  { key: 'createdAt', label: 'Added' },
  {
    key: 'actions',
    label: '',
    width: 140,
    render: (r, { onEdit, onDelete }) => (
      <div className="ad-actions-row">
        <button
          type="button"
          className="ad-btn ad-btn--ghost ad-btn--sm"
          onClick={() => onEdit(r)}
        >
          Edit
        </button>
        <button
          type="button"
          className="ad-btn ad-btn--ghost ad-btn--sm ad-btn--danger"
          onClick={() => onDelete(r)}
        >
          Delete
        </button>
      </div>
    ),
  },
];

export default function Presets() {
  const [modal, setModal] = useState(null);
  const [search, setSearch] = useState('');
  const [codesFilter, setCodesFilter] = useState('all');
  const { loading, data: presets, setData: setPresets } = useAdminQuery(
    () => admin.getPresets().then((data) => (Array.isArray(data) ? data : [])),
    [],
  );
  const presetRows = presets ?? [];

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return presetRows.filter((p) => {
      if (q) {
        const names = Array.isArray(p.names) ? p.names : [];
        const haystack = [p.name, ...names].filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      const count = Array.isArray(p.names) ? p.names.length : 0;
      if (codesFilter === 'single' && count !== 1) return false;
      if (codesFilter === 'multi' && count <= 1) return false;
      return true;
    });
  }, [presetRows, search, codesFilter]);

  const closeModal = () => setModal(null);

  const create = async (preset) => {
    const created = await admin.createPreset(preset);
    setPresets((prev) => [
      ...(prev ?? []),
      created ?? { ...preset, id: Date.now(), createdAt: new Date().toLocaleDateString() },
    ]);
    closeModal();
    presetAppliedAlert(created, { isUpdate: false });
  };

  const update = async (preset) => {
    const updated = await admin.updatePreset(modal.id, preset);
    setPresets((prev) =>
      (prev ?? []).map((p) =>
        p.id === modal.id
          ? { ...p, ...updated, id: modal.id }
          : p,
      ),
    );
    closeModal();
    presetAppliedAlert(updated, { isUpdate: true });
  };

  const del = async (preset) => {
    const label = preset.names?.[0] || preset.name || 'this preset';
    if (!window.confirm(`Delete preset "${label}"?`)) return;
    try {
      await admin.deletePreset(preset.id);
      setPresets((prev) => (prev ?? []).filter((p) => p.id !== preset.id));
    } catch (err) {
      window.alert(err?.message || 'Could not delete preset.');
    }
  };

  const cols = COLS.map((c) =>
    c.key === 'actions'
      ? { ...c, render: (r) => c.render(r, { onEdit: setModal, onDelete: del }) }
      : c,
  );

  const isAdd = modal === 'add';

  return (
    <Page
      title="Presets"
      action={
        <button
          type="button"
          className="ad-btn ad-btn--primary"
          onClick={() => setModal('add')}
        >
          <Icon name="plus" size={16} />
          Add
        </button>
      }
    >
      <AdminContentLoader loading={loading}>
        <Card title="Presets">
          <Toolbar>
            <input
              className="ad-input ad-input--grow"
              placeholder="Search by code or name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="ad-select"
              value={codesFilter}
              onChange={(e) => setCodesFilter(e.target.value)}
            >
              <option value="all">All aliases</option>
              <option value="single">Single code</option>
              <option value="multi">Multiple codes</option>
            </select>
          </Toolbar>
          <DataTable
            columns={cols}
            rows={filteredRows}
            empty={
              presetRows.length === 0
                ? 'No presets yet — click Add to create one'
                : 'No presets match your filters'
            }
            pageSize={12}
          />
        </Card>
      </AdminContentLoader>

      <Modal
        open={!!modal}
        onClose={closeModal}
        title={isAdd ? 'New preset' : 'Edit preset'}
        wide
      >
        {modal && (
          <PresetForm
            key={isAdd ? 'add' : modal.id}
            initial={isAdd ? undefined : { imageUrl: modal.imageUrl, names: modal.names }}
            onSave={isAdd ? create : update}
            onCancel={closeModal}
            saveLabel={isAdd ? 'Save preset' : 'Save changes'}
          />
        )}
      </Modal>
    </Page>
  );
}

function PresetForm({ initial, onSave, onCancel, saveLabel = 'Save preset' }) {
  const [imageUrl, setImageUrl] = useState(initial?.imageUrl ?? '');
  const [names, setNames] = useState(initial?.names ?? []);
  const [input, setInput] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef();
  const inputRef = useRef();

  const loadFile = (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = (e) => setImageUrl(e.target.result);
    reader.readAsDataURL(file);
  };

  const commit = () => {
    const v = input.trim();
    if (v && !names.includes(v)) setNames((prev) => [...prev, v]);
    setInput('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    } else if (e.key === 'Backspace' && input === '' && names.length > 0) {
      setNames((prev) => prev.slice(0, -1));
    }
  };

  const remove = (n) => setNames((prev) => prev.filter((x) => x !== n));

  const canSave = imageUrl && names.length > 0;

  const submit = async () => {
    if (!canSave || saving) return;
    setSaving(true);
    try {
      await onSave({ imageUrl, names });
    } catch (err) {
      window.alert(err?.message || 'Could not save preset.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="ad-preset-layout">
        <div className="ad-preset-left">
          <div className="ad-field">
            <span className="ad-field__label">Image</span>
            <div
              className={`ad-dropzone${imageUrl ? ' ad-dropzone--filled' : ''}${dragOver ? ' ad-dropzone--over' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                loadFile(e.dataTransfer.files[0]);
              }}
              onClick={() => fileRef.current.click()}
            >
              {safePreviewImageUrl(imageUrl) ? (
                <img src={safePreviewImageUrl(imageUrl)} alt="Uploaded" className="ad-dropzone__img" />
              ) : (
                <div className="ad-dropzone__hint">
                  <Icon name="upload" size={22} />
                  <span>Click or drag & drop</span>
                  <small>PNG, JPG, WEBP</small>
                </div>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={(e) => loadFile(e.target.files[0])}
            />
            {imageUrl && (
              <button
                type="button"
                className="ad-btn ad-btn--ghost ad-btn--sm"
                style={{ marginTop: 6, alignSelf: 'flex-start' }}
                onClick={() => { setImageUrl(''); fileRef.current.value = ''; }}
              >
                Remove image
              </button>
            )}
          </div>

          <Field label="Codes / Names">
            <div
              className="ad-tag-input"
              onClick={() => inputRef.current?.focus()}
            >
              {names.map((n) => (
                <span key={n} className="ad-tag">
                  {n}
                  <button
                    type="button"
                    className="ad-tag__rm"
                    onClick={(e) => { e.stopPropagation(); remove(n); }}
                  >
                    ×
                  </button>
                </span>
              ))}
              <input
                ref={inputRef}
                className="ad-tag-input__field"
                placeholder={names.length === 0 ? 'Type and press Enter…' : ''}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                onBlur={commit}
              />
            </div>
            <small className="ad-field-hint">
              Press Enter after each code — you can add as many as you like
            </small>
          </Field>
        </div>

        <div className="ad-preset-right">
          <span className="ad-preset-preview-label">Card preview</span>
          <div className="ad-preset-card-wrap">
            <div className="featured-bets__card" style={{ pointerEvents: 'none' }}>
              <div className="featured-bets__media">
                {safePreviewImageUrl(imageUrl) ? (
                  <img alt="" className="featured-bets__media-img" src={safePreviewImageUrl(imageUrl)} />
                ) : (
                  <div className="ad-preset-card-img-empty" />
                )}
                <div className="featured-bets__media-shade" aria-hidden="true" />
              </div>
              <div className="featured-bets__body">
                <div className="featured-bets__meta">
                  <div className="featured-bets__date">
                    <span className="featured-bets__date-text">17 May 2026</span>
                  </div>
                  <h3 className="featured-bets__title">
                    {names[0] ?? 'Preset name preview'}
                  </h3>
                </div>
                <div className="featured-bets__actions">
                  <button type="button" className="featured-bets__btn featured-bets__btn--yes">
                    <span className="featured-bets__btn-label">Yes</span>
                    <span className="featured-bets__btn-odds">1.85</span>
                  </button>
                  <button type="button" className="featured-bets__btn featured-bets__btn--no">
                    <span className="featured-bets__btn-label">No</span>
                    <span className="featured-bets__btn-odds">2.10</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {safePreviewImageUrl(imageUrl) && (
            <div className="ad-preset-img-ratio">
              <span className="ad-preset-preview-label">Image (natural ratio)</span>
              <img src={safePreviewImageUrl(imageUrl)} alt="" className="ad-preset-img-natural" />
            </div>
          )}
        </div>
      </div>

      <div className="ad-modal__footer">
        <button type="button" className="ad-btn ad-btn--ghost" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button
          type="button"
          className="ad-btn ad-btn--primary"
          disabled={!canSave || saving}
          onClick={submit}
        >
          {saveLabel}
        </button>
      </div>
    </>
  );
}
