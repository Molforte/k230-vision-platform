"""
steel_ball_tracker.py — 钢球多目标跟踪器

最近邻匹配 + 滑动平均滤波，抑制单帧误检与交叉幻影。
新目标需连续 MIN_HITS 帧命中后才输出。
"""


class SteelBallTracker:
    """钢球多目标跟踪器

    dets 格式: [(cx, cy, w, h, dist, area), ...]  已面积降序
    输出格式: [{'id','cx','cy','w','h','dist','hits'}, ...]
    """

    def __init__(self, smooth_win=5, lost_frames=5, match_gate=80,
                 n_max=5, max_tracks=8, min_hits=2):
        self.smooth_win  = smooth_win
        self.lost_frames = lost_frames
        self.match_gate  = match_gate
        self.n_max       = n_max
        self.max_tracks  = max_tracks
        self.min_hits    = min_hits

        self.tracks       = []
        self._next_id     = 1

    # ── 内部 ──────────────────────────────────────────

    def _new_track(self):
        t = {'id': self._next_id,
             'cx': 0.0, 'cy': 0.0, 'w': 0.0, 'h': 0.0, 'dist': 0.0,
             'win': [], 'lost': 0, 'hits': 0}
        self._next_id += 1
        return t

    def _push_sample(self, t, cx, cy, w, h, dist):
        """样本入滑动窗并重算均值"""
        win = t['win']
        win.append((cx, cy, w, h, dist))
        if len(win) > self.smooth_win:
            win.pop(0)
        n = len(win)
        sx = sy = sw = sh = sd = 0.0
        for s in win:
            sx += s[0]; sy += s[1]; sw += s[2]; sh += s[3]; sd += s[4]
        t['cx']   = sx / n
        t['cy']   = sy / n
        t['w']    = sw / n
        t['h']    = sh / n
        t['dist'] = sd / n
        t['lost'] = 0
        t['hits'] += 1

    # ── 对外 ──────────────────────────────────────────

    def update(self, dets):
        """dets: [(cx,cy,w,h,dist,area),...] → 本帧可输出的 track 列表"""
        matched_ids = []
        out = []

        for d in dets:
            # 贪心最近邻 (球心曼哈顿距离)
            best   = None
            best_d = self.match_gate
            for t in self.tracks:
                if t['id'] in matched_ids:
                    continue
                dd = abs(t['cx'] - d[0]) + abs(t['cy'] - d[1])
                if dd < best_d:
                    best   = t
                    best_d = dd

            if best is None:
                if len(self.tracks) >= self.max_tracks:
                    continue
                best = self._new_track()
                self.tracks.append(best)

            self._push_sample(best, d[0], d[1], d[2], d[3], d[4])
            matched_ids.append(best['id'])
            if best['hits'] >= self.min_hits:
                out.append(best)

        # 未认领轨迹 lost+1，超时删除
        i = 0
        while i < len(self.tracks):
            if self.tracks[i]['id'] not in matched_ids:
                self.tracks[i]['lost'] += 1
            if self.tracks[i]['lost'] > self.lost_frames:
                self.tracks.pop(i)
            else:
                i += 1

        # 按平滑后面积降序
        for i in range(1, len(out)):
            cur = out[i]
            ca  = cur['w'] * cur['h']
            j   = i - 1
            while j >= 0 and out[j]['w'] * out[j]['h'] < ca:
                out[j + 1] = out[j]
                j -= 1
            out[j + 1] = cur

        return out[:self.n_max]
