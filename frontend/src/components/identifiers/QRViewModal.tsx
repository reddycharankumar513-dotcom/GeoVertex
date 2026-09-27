// Phase 12 — QR Code View Modal for GeoVertex Technical 3D Identifiers
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

import React from 'react';
import { X, Download, ShieldAlert, QrCode } from 'lucide-react';
import { getQrUrl } from '../../api/identifier';

interface QRViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  identifierId: string;
  identifierValue: string;
}

export const QRViewModal: React.FC<QRViewModalProps> = ({
  isOpen,
  onClose,
  identifierId,
  identifierValue,
}) => {
  if (!isOpen) return null;

  const qrUrl = getQrUrl(identifierId, 'png');

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = qrUrl;
    link.download = `geovertex-identifier-${identifierValue}.png`;
    link.click();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-sm mx-4 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <QrCode className="w-5 h-5 text-teal-400" />
            <h2 className="text-sm font-semibold text-slate-100">
              GeoVertex Technical 3D Identifier QR
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 flex flex-col items-center gap-4">
          {/* Identifier value */}
          <p className="text-xs font-mono text-teal-300 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-center break-all w-full">
            {identifierValue}
          </p>

          {/* QR Image */}
          <div className="bg-white p-3 rounded-xl shadow-lg">
            <img
              src={qrUrl}
              alt={`QR code for ${identifierValue}`}
              className="w-56 h-56 object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).alt = 'QR code unavailable';
              }}
            />
          </div>

          {/* Download */}
          <button
            onClick={handleDownload}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-sm font-medium transition"
          >
            <Download className="w-4 h-4" />
            Download QR Code (PNG)
          </button>

          {/* Disclaimer */}
          <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-950 border border-amber-500/20 rounded-lg p-3">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
            <p>
              This QR encodes a <strong className="text-amber-300">GeoVertex Technical 3D Identifier</strong>.
              It is NOT an official ULPIN or legal property identifier.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
