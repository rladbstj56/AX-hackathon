"use client";

import { useRef, useState, useTransition } from "react";
import { addRestaurant } from "@/app/actions";
import StarRating from "@/components/StarRating";
import { CATEGORIES } from "@/types";

const DISTRICTS = [
  "강남구", "강동구", "강북구", "강서구", "관악구",
  "광진구", "구로구", "금천구", "노원구", "도봉구",
  "동대문구", "동작구", "마포구", "서대문구", "서초구",
  "성동구", "성북구", "송파구", "양천구", "영등포구",
  "용산구", "은평구", "종로구", "중구", "중랑구",
];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-semibold text-gray-600">{label}</label>
      {children}
    </div>
  );
}

const inputCls =
  "w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-400";

export default function RestaurantForm() {
  const formRef = useRef<HTMLFormElement>(null);
  const [rating, setRating] = useState(0);
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
      await addRestaurant(formData);
      formRef.current?.reset();
      setRating(0);
    });
  }

  return (
    <form
      ref={formRef}
      onSubmit={handleSubmit}
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4"
    >
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <Field label="상호명 *">
            <input name="name" required placeholder="가게 이름" className={inputCls} />
          </Field>
        </div>

        <Field label="카테고리">
          <select name="category" className={inputCls}>
            <option value="">선택 안함</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>

        <Field label="대표메뉴 *">
          <input name="menu" required placeholder="대표 메뉴" className={inputCls} />
        </Field>

        <Field label="구 (지역)">
          <select name="district" className={inputCls}>
            <option value="">선택 안함</option>
            {DISTRICTS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </Field>

        <Field label="동 (동네)">
          <input name="neighborhood" placeholder="예) 역삼동" className={inputCls} />
        </Field>

        <div className="col-span-2">
          <Field label="주소">
            <input name="address" placeholder="상세 주소 (선택)" className={inputCls} />
          </Field>
        </div>

        <div className="col-span-2">
          <Field label="전화번호 / 예약번호">
            <input name="phone" placeholder="예) 02-1234-5678" className={inputCls} />
          </Field>
        </div>
      </div>

      <Field label="별점 *">
        <StarRating value={rating} onChange={setRating} />
        {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
      </Field>

      <button
        type="submit"
        disabled={isPending}
        className="w-full py-3 bg-red-500 hover:bg-red-600 disabled:opacity-60 text-white font-semibold rounded-lg transition-colors"
      >
        {isPending ? "추가 중…" : "추가하기"}
      </button>
    </form>
  );
}
