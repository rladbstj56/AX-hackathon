import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Supabase 연결 전까지는 null로 유지됩니다.
// .env 파일에 VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY를 설정하면 자동으로 연결됩니다.
export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null
