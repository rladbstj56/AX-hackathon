"use client";

import { useRef, useState, useTransition } from "react";
import { updateRestaurant } from "@/app/actions";
import StarRating from "@/components/StarRating";
import { CATEGORIES, Restaurant } from "@/types";

const DISTRICTS = [
  "강남구", "강동구", "강북구", "강서구", "관악구",
  "광진구", "구로구", "금천구", "노원구", "도봉구",
  "동대문구", "동작구", "마포구", "서대문구", "서초구",
  "성동구", "성북구", "송파구", "양천구", "영등포구",
  "용산구", "은평구", "종로구", "중구", "중랑구",
];

const inputCls =
  "w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-semibold text-gray-600">{label}</label>
      {children}
    </div>
  );
}

export default function EditModal({
  restaurant,
  onClose,
}: {
  restaurant: Restaurant;
  onClose: () => void;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [rating, setRating] = useState(restaurant.rating);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (rating === 0) {
      setError("별점을 선택해주세요.");
      return;
    }
    setError("");

    const formData = new FormData(e.currentTarget);
    formData.set("rating", String(rating));

    startTransition(async () => {
      await updateRestaurant(restaurant.id, formData);
      onClose();
    });
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-gray-800">맛집 수정</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="상호명 *">
                <input
                  name="name"
                  required
                  defaultValue={restaurant.name}
                  className={inputCls}
                />
              </Field>
            </div>

            <Field label="카테고리">
              <select name="category" defaultValue={restaurant.category ?? ""} className={inputCls}>
                <option value="">선택 안함</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>

            <Field label="대표메뉴 *">
              <input
                name="menu"
                required
                defaultValue={restaurant.menu}
                className={inputCls}
              />
            </Field>

            <Field label="구 (지역)">
              <select name="district" defaultValue={restaurant.district ?? ""} className={inputCls}>
                <option value="">선택 안함</option>
                {DISTRICTS.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </Field>

            <Field label="동 (동네)">
              <input
                name="neighborhood"
                defaultValue={restaurant.neighborhood ?? ""}
                placeholder="예) 역삼동"
                className={inputCls}
              />
            </Field>

            <div className="col-span-2">
              <Field label="주소">
                <input
                  name="address"
                  defaultValue={restaurant.address ?? ""}
                  placeholder="상세 주소 (선택)"
                  className={inputCls}
                />
              </Field>
            </div>

            <div className="col-span-2">
              <Field label="전화번호 / 예약번호">
                <input
                  name="phone"
                  defaultValue={restaurant.phone ?? ""}
                  placeholder="예) 02-1234-5678"
                  className={inputCls}
                />
              </Field>
            </div>
          </div>

          <Field label="별점 *">
            <StarRating value={rating} onChange={setRating} />
            {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
          </Field>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 border border-gray-200 text-gray-600 font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex-1 py-3 bg-red-500 hover:bg-red-600 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
            >
              {isPending ? "저장 중…" : "저장하기"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
