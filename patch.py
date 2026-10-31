#!/usr/bin/env python3
# HORI PS4-133 quirk patch applier for BlueZ sdp.c (version-tolerant)
import sys, os
HELPERS = r"""
/* ---- HORI PS4-133 quirk helpers (begin) ---- */
struct quirk_attr { uint16_t id; uint8_t type; uint32_t val; };
/* fake PnP record of a Sony PS4 host */
static const struct quirk_attr quirk_pnp[] = {
	{ 0x0000, 0x0a, 0x00010000 },	/* record handle */
	{ 0x0001, 0xff, 0x1200 },	/* class id list: PnP */
	{ 0x0200, 0x09, 0x0103 },	/* spec id */
	{ 0x0201, 0x09, 0x054c },	/* vendor id: Sony */
	{ 0x0202, 0x09, 0x05c4 },	/* product id */
	{ 0x0203, 0x09, 0x0100 },	/* version */
	{ 0x0204, 0x28, 0x01 },		/* primary record */
	{ 0x0205, 0x09, 0x0002 },	/* vendor id source: USB */
};

static int quirk_des_hdr(const uint8_t *p, int avail, int *dlen)
{
	if (avail < 2) return -1;
	if (p[0] == 0x35) { *dlen = p[1]; return 2; }
	if (p[0] == 0x36 && avail >= 3) { *dlen = (p[1] << 8) | p[2]; return 3; }
	return -1;
}

static int quirk_attr_wanted(const uint8_t *ids, int idlen, uint16_t id)
{
	int i = 0;
	if (idlen <= 0) return 1;
	while (i < idlen) {
		if (ids[i] == 0x09 && i + 3 <= idlen) {
			if (((ids[i+1] << 8) | ids[i+2]) == id) return 1;
			i += 3;
		} else if (ids[i] == 0x0a && i + 5 <= idlen) {
			uint16_t lo = (ids[i+1] << 8) | ids[i+2];
			uint16_t hi = (ids[i+3] << 8) | ids[i+4];
			if (id >= lo && id <= hi) return 1;
			i += 5;
		} else
			return 1;
	}
	return 0;
}

static int quirk_build_attrs(const uint8_t *ids, int idlen, uint8_t *out)
{
	int n = 0;
	unsigned int k;
	for (k = 0; k < sizeof(quirk_pnp) / sizeof(quirk_pnp[0]); k++) {
		const struct quirk_attr *a = &quirk_pnp[k];
		if (!quirk_attr_wanted(ids, idlen, a->id)) continue;
		out[n++] = 0x09; out[n++] = a->id >> 8; out[n++] = a->id & 0xff;
		switch (a->type) {
		case 0x09: out[n++] = 0x09; out[n++] = a->val >> 8; out[n++] = a->val & 0xff; break;
		case 0x0a: out[n++] = 0x0a; out[n++] = a->val >> 24; out[n++] = a->val >> 16; out[n++] = a->val >> 8; out[n++] = a->val; break;
		case 0x28: out[n++] = 0x28; out[n++] = a->val; break;
		case 0xff: out[n++] = 0x35; out[n++] = 0x03; out[n++] = 0x19; out[n++] = a->val >> 8; out[n++] = a->val & 0xff; break;
		}
	}
	return n;
}

/* returns response length written to rsp, or -1 */
static int quirk_answer(const uint8_t *req, int reqlen, uint8_t *rsp)
{
	const sdp_pdu_hdr_t *rh = (const sdp_pdu_hdr_t *) req;
	sdp_pdu_hdr_t *oh = (sdp_pdu_hdr_t *) rsp;
	const uint8_t *p = req + sizeof(sdp_pdu_hdr_t);
	int avail = reqlen - sizeof(sdp_pdu_hdr_t), h, dlen;
	uint8_t attrs[128];
	int n, plen;

	oh->tid = rh->tid;
	if (rh->pdu_id == SDP_SVC_SEARCH_REQ) {
		oh->pdu_id = SDP_SVC_SEARCH_RSP;
		rsp[5] = 0; rsp[6] = 1; rsp[7] = 0; rsp[8] = 1;	/* total 1, current 1 */
		rsp[9] = 0; rsp[10] = 1; rsp[11] = 0; rsp[12] = 0;	/* handle 0x10000 */
		rsp[13] = 0;						/* cstate */
		oh->plen = htons(9);
		return 14;
	}
	if (rh->pdu_id == SDP_SVC_ATTR_REQ) {
		/* handle(4) maxcount(2) attr id list */
		p += 6; avail -= 6;
	} else {
		/* search pattern DES, maxcount(2), attr id list */
		h = quirk_des_hdr(p, avail, &dlen);
		if (h < 0) return -1;
		p += h + dlen; avail -= h + dlen;
		p += 2; avail -= 2;
	}
	h = quirk_des_hdr(p, avail, &dlen);
	if (h < 0 || dlen > avail - h) { dlen = 0; h = 0; }
	n = quirk_build_attrs(p + h, dlen, attrs);

	if (rh->pdu_id == SDP_SVC_ATTR_REQ) {
		oh->pdu_id = SDP_SVC_ATTR_RSP;
		rsp[5] = 0; rsp[6] = n + 2;
		rsp[7] = 0x35; rsp[8] = n;
		memcpy(rsp + 9, attrs, n);
		rsp[9 + n] = 0;
		plen = 2 + 2 + n + 1;
	} else {
		oh->pdu_id = SDP_SVC_SEARCH_ATTR_RSP;
		rsp[5] = 0; rsp[6] = n + 4;
		rsp[7] = 0x35; rsp[8] = n + 2;
		rsp[9] = 0x35; rsp[10] = n;
		memcpy(rsp + 11, attrs, n);
		rsp[11 + n] = 0;
		plen = 2 + 4 + n + 1;
	}
	oh->plen = htons(plen);
	return plen + sizeof(sdp_pdu_hdr_t);
}
/* ---- HORI PS4-133 quirk helpers (end) ---- */

"""
BLOCK = r"""
	if (rsphdr->pdu_id == SDP_SVC_SEARCH_REQ ||
			rsphdr->pdu_id == SDP_SVC_ATTR_REQ ||
			rsphdr->pdu_id == SDP_SVC_SEARCH_ATTR_REQ) {
		/* Quirk (HORI PS4-133): the peer sends its own SDP requests
		 * (asking for our PnP record) on our client channel and
		 * treats our request as the answer. Answer as a Sony PS4
		 * host, then re-send our own request once. */
		uint8_t rbuf[200];
		int rlen = quirk_answer(rspbuf, n, rbuf);

		SDPERR("Quirk: peer SDP request 0x%02x tid %u -> reply %d bytes",
			rsphdr->pdu_id, ntohs(rsphdr->tid), rlen);
		if (rlen > 0)
			sdp_send_req(session, rbuf, rlen);
		if (rsphdr->pdu_id != SDP_SVC_SEARCH_REQ &&
				t->quirk_resent == 0) {
			t->quirk_resent = 1;
			SDPERR("Quirk: re-sending our request tid %u",
				ntohs(reqhdr->tid));
			sdp_send_req(session, t->reqbuf,
				ntohs(reqhdr->plen) + sizeof(sdp_pdu_hdr_t));
		}
		free(rspbuf);
		return 0;
	}

"""
root = sys.argv[1]
cand = None
for c in ("lib/bluetooth/sdp.c", "lib/sdp.c"):
    if os.path.exists(os.path.join(root, c)):
        cand = os.path.join(root, c); break
if not cand:
    sys.exit("ERROR: sdp.c not found under " + root)
s = open(cand, encoding="utf-8", errors="surrogateescape").read()
if "quirk_resent" in s:
    print("already patched:", cand); sys.exit(0)


def need(haystack, needle, start=0):
    """Locate an anchor or exit with a clear, actionable message instead of a
    raw Python traceback, so an unrecognised BlueZ layout fails readably."""
    pos = haystack.find(needle, start)
    if pos < 0:
        sys.exit(
            "ERROR: could not find the code anchor:\n    " + needle + "\n"
            "in " + cand + "\n"
            "This BlueZ version's sdp.c layout is not recognised, so the patch\n"
            "was NOT applied (your source is unchanged). Please open an issue at\n"
            "https://github.com/momomorin/hori-ps4-133-steamdeck/issues with the\n"
            "output of `bluetoothctl --version` so support can be added."
        )
    return pos


# verified to apply on BlueZ 5.55 .. 5.87; anchors are stable across that range
i = need(s, "struct sdp_transaction {")
j = need(s, "\n};", i)
s = s[:j] + "\n\tint quirk_resent;" + s[j:]
i = need(s, "int sdp_process(sdp_session_t *session)")
s = s[:i] + HELPERS.strip("\n") + "\n\n" + s[i:]
i = need(s, "if (reqhdr->tid != rsphdr->tid) {")
ls = s.rfind("\n", 0, i) + 1
s = s[:ls] + BLOCK.strip("\n") + "\n\n" + s[ls:]
open(cand, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("patched:", cand)
