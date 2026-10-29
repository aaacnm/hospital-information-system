import { useEffect, useState } from 'react';
import { apiClient } from './client';
export function useData<T>(url: string | null, version = 0) {
    const [data, setData] = useState<T | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        let active = true;
        setLoading(true);
        setError(null);
        setData(null);
        if (url === null) {
            setLoading(false);
            return;
        }
        apiClient.get<T>(url).then(value => { if (active)
            setData(value); })
            .catch(reason => { if (active)
            setError(reason); })
            .finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, [url, version]);
    return { data, error, loading };
}
export const localDay = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
export const formatTime = (v: string) => new Date(v.endsWith('Z') || /[+-]\d\d:\d\d$/.test(v) ? v : v + 'Z').toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });

export const dateBefore=(days:number)=>new Date(Date.parse(localDay()+'T00:00:00Z')-days*86400000).toISOString().slice(0,10);
