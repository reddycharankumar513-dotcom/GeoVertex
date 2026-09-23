import React, { useState, useEffect, useRef } from 'react';
import { Search, Loader2, MapPin, Building, Home, X } from 'lucide-react';
import { gisApi } from '../../api/gis';

interface SearchResultItem {
  id: string;
  type: 'PARCEL' | 'PROPERTY' | 'BUILDING';
  identifier: string;
  subtitle: string;
  status: string;
  item: any;
}

interface SearchBarProps {
  onSelectResult: (type: 'PARCEL' | 'PROPERTY' | 'BUILDING', id: string, item: any) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSelectResult }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const [parcelRes, propRes, bldRes] = await Promise.all([
          gisApi.listParcels({ query: query.trim(), size: 5 }),
          gisApi.listProperties({ query: query.trim(), size: 5 }),
          gisApi.listBuildings({ query: query.trim(), size: 5 }),
        ]);

        const combined: SearchResultItem[] = [];

        parcelRes.items?.forEach((p) => {
          combined.push({
            id: p.id,
            type: 'PARCEL',
            identifier: p.parcel_code,
            subtitle: `Parcel ${p.parcel_number} (${p.land_use}) - ${p.area} m²`,
            status: p.status,
            item: p,
          });
        });

        propRes.items?.forEach((pr) => {
          combined.push({
            id: pr.id,
            type: 'PROPERTY',
            identifier: pr.property_reference,
            subtitle: pr.address,
            status: pr.status,
            item: pr,
          });
        });

        bldRes.items?.forEach((b) => {
          combined.push({
            id: b.id,
            type: 'BUILDING',
            identifier: b.building_reference,
            subtitle: `${b.building_type} - ${b.area} m²`,
            status: b.status,
            item: b,
          });
        });

        setResults(combined);
        setIsOpen(true);
      } catch (err) {
        console.error('Search error:', err);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getTypeBadge = (type: SearchResultItem['type']) => {
    switch (type) {
      case 'PARCEL':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800">
            <Home className="w-3 h-3" />
            <span>PARCEL</span>
          </span>
        );
      case 'PROPERTY':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-950/80 text-amber-300 border border-amber-800">
            <MapPin className="w-3 h-3" />
            <span>PROPERTY</span>
          </span>
        );
      case 'BUILDING':
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950/80 text-sky-300 border border-sky-800">
            <Building className="w-3 h-3" />
            <span>BUILDING</span>
          </span>
        );
    }
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => query.trim().length >= 2 && setIsOpen(true)}
          placeholder="Search parcels, survey #, properties, or buildings..."
          className="w-full pl-9 pr-9 py-2 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/40 shadow-xl backdrop-blur transition-all"
        />
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
        {loading ? (
          <Loader2 className="w-4 h-4 text-emerald-400 absolute right-3 top-2.5 animate-spin" />
        ) : query ? (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
              setIsOpen(false);
            }}
            className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : null}
      </div>

      {/* Results Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-50 max-h-80 overflow-y-auto">
          {results.length > 0 ? (
            <div className="py-1 divide-y divide-slate-800/60">
              {results.map((res) => (
                <div
                  key={`${res.type}-${res.id}`}
                  onClick={() => {
                    onSelectResult(res.type, res.id, res.item);
                    setIsOpen(false);
                  }}
                  className="px-3.5 py-2.5 hover:bg-slate-800/60 cursor-pointer flex items-center justify-between transition-colors"
                >
                  <div className="min-w-0 pr-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-semibold text-slate-100 truncate font-mono">
                        {res.identifier}
                      </span>
                      {getTypeBadge(res.type)}
                    </div>
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">{res.subtitle}</p>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 uppercase">
                    {res.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="px-4 py-6 text-center text-xs text-slate-400">
              No matching cadastral features found
            </div>
          )}
        </div>
      )}
    </div>
  );
};
