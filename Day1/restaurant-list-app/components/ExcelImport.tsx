"use client";

import { useState, useTransition } from "react";
import * as XLSX from "xlsx";
import { importRestaurants } from "@/app/actions";
import StarRating from "@/components/StarRating";
import { CATEGORIES, Category } from "@/types";

type ImportRow = {
  name: string;
  menu: string;
  phone: string | null;
  address: string | null;
  district: string;
  neighborhood: string;
  rating: number;
  category: string | null;
};

export default function ExcelImport() {
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [isPending, startTransition] = useTransition();
  const [done, setDone] = useState(false);

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setDone(false);

    const reader = new FileReader();
    reader.onload = (ev) => {
      const data = new Uint8Array(ev.target?.result as ArrayBuffer);
      const wb = XLSX.read(data, { type: "array" });

      const parsed: ImportRow[] = [];

      const targetSheets = wb.SheetNames.filter((s) => s !== "회사부근 맛집->");

      targetSheets.forEach((sheetName) => {
        const ws = wb.Sheets[sheetName];
        if (!ws) return;

        const sheetRows = XLSX.utils.sheet_to_json(ws, {
          header: 1,
          defval: "",
        }) as string[][];

        sheetRows.forEach((row) => {
          const name = String(row[0] ?? "").trim().replace(/[\r\n]+/g, " ");
          const menu = String(row[1] ?? "").trim().replace(/[\r\n]+/g, " ");
          const phone = String(row[2] ?? "").trim() || null;
          const rawAddress = String(row[3] ?? "").trim();

          if (!name || !menu) return;
          if (name.includes("상  호  명") || name.includes("마우스")) return;

          const neighborhood = rawAddress.split(" ")[0] ?? "";
          const address = rawAddress ? `중구 ${rawAddress}` : null;

          parsed.push({
            name,
            menu,
            phone,
            address,
            district: "중구",
            neighborhood,
            rating: 3,
            category: null,
          });
        });
      });

      setRows(parsed);
    };
    reader.readAsArrayBuffer(file);
    e.target.value = "";
  }

  function updateRow<K extends keyof ImportRow>(index: number, key: K, value: ImportRow[K]) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [key]: value } : r)));
  }

  function removeRow(index: number) {
    setRows((prev) => prev.filter((_, i) => i !== index));
  }

  function handleImport() {
    startTransition(async () => {
      await importRestaurants(rows);
      setRows([]);
      setDone(true);
    });
  }

  const inputCls =
    "w-full px-2 py-1 border border-gray-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-red-400";

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-700">엑셀 가져오기</h2>
        <label className="cursor-pointer px-4 py-2 bg-red-50 hover:bg-red-100 text-red-500 text-sm font-medium rounded-lg transition-colors">
          📂 파일 선택 (.xlsx)
          <input
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFile}
            className="hidden"
          />
        </label>
      </div>

      {done && (
        <p className="text-sm text-green-600 font-medium">✅ 가져오기 완료!</p>
      )}

      {rows.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">
            <span className="font-semibold text-gray-700">{rows.length}개</span> 항목을 가져올 예정입니다.
            별점과 카테고리를 미리 수정할 수 있습니다.
          </p>

          <div className="overflow-x-auto rounded-lg border border-gray-100">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-3 py-2 text-left">상호명</th>
                  <th className="px-3 py-2 text-left">메뉴</th>
                  <th className="px-3 py-2 text-left">동네</th>
                  <th className="px-3 py-2 text-left">카테고리</th>
                  <th className="px-3 py-2 text-left">별점</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <input
                        value={row.name}
                        onChange={(e) => updateRow(i, "name", e.target.value)}
                        className={inputCls}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        value={row.menu}
                        onChange={(e) => updateRow(i, "menu", e.target.value)}
                        className={inputCls}
                      />
                    </td>
                    <td className="px-3 py-2 text-gray-400 text-xs whitespace-nowrap">
                      {row.neighborhood}
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={row.category ?? ""}
                        onChange={(e) =>
                          updateRow(i, "category", e.target.value || null)
                        }
                        className={inputCls}
                      >
                        <option value="">선택 안함</option>
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <StarRating
                        value={row.rating}
                        onChange={(v) => updateRow(i, "rating", v)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => removeRow(i)}
                        className="text-gray-300 hover:text-red-400 transition-colors"
                        title="제외"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={handleImport}
            disabled={isPending}
            className="w-full py-3 bg-red-500 hover:bg-red-600 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
          >
            {isPending ? "가져오는 중…" : `${rows.length}개 전체 가져오기`}
          </button>
        </div>
      )}
    </div>
  );
}
