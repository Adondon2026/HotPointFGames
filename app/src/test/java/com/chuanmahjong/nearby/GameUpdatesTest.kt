package com.chuanmahjong.nearby

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class GameUpdatesTest {
    private val source = "a".repeat(40)
    private val tag = "game-250-1-aaaaaaaaaaaa"
    private fun manifest(host: Int = 4, epoch: Long = 123L, hash: String = "b".repeat(64), version: String = tag, commit: String = source): String =
        JSONObject().put("schema", 1).put("version", version).put("source", commit)
            .put("sourceEpoch", epoch).put("sha256", hash).put("size", 100).put("minHostVersionCode", host).toString()

    @Test fun directManifestSelectsPinnedRelease() {
        assertEquals("https://github.com/Adondon2026/HotPointFGames/releases/latest/download/game-update.json", GameUpdates.LATEST_MANIFEST)
        val update = GameUpdates.resolveLatest(manifest(), null)!!
        assertEquals(tag, update.tag)
        assertEquals(source, update.info.source)
    }

    @Test fun unchangedOrOlderReleaseIsSkipped() {
        val local = GameUpdates.resolveLatest(manifest(), null)!!.info
        assertNull(GameUpdates.resolveLatest(manifest(), local))
        assertNull(GameUpdates.resolveLatest(manifest(epoch = 122, hash = "c".repeat(64)), local))
        assertNotNull(GameUpdates.resolveLatest(manifest(epoch = 124, hash = "c".repeat(64)), local))
    }

    @Test fun invalidManifestAndIncompatibleHostRejected() {
        for (raw in listOf(manifest(host = 6), manifest(version = "android-v1.4"), manifest(commit = "c".repeat(40)), manifest(hash = "not-a-hash"))) {
            try {
                GameUpdates.resolveLatest(raw, null)
                fail("Invalid manifest accepted")
            } catch (_: IllegalArgumentException) { }
        }
    }
}
