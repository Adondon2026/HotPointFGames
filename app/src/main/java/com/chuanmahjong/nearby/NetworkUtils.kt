package com.chuanmahjong.nearby

import java.net.Inet4Address
import java.net.NetworkInterface
import java.util.Collections

object NetworkUtils {
    data class Candidate(val interfaceName: String, val address: String, val score: Int)

    fun localIpv4Candidates(): List<Candidate> {
        val result = mutableListOf<Candidate>()
        val interfaces = try {
            Collections.list(NetworkInterface.getNetworkInterfaces())
        } catch (_: Throwable) {
            emptyList()
        }

        for (networkInterface in interfaces) {
            val name = networkInterface.name.orEmpty().lowercase()
            val usable = try {
                networkInterface.isUp && !networkInterface.isLoopback
            } catch (_: Throwable) {
                false
            }
            if (!usable || isClearlyNotHotspot(name)) continue

            for (address in Collections.list(networkInterface.inetAddresses)) {
                if (address !is Inet4Address || address.isLoopbackAddress ||
                    address.isLinkLocalAddress || !address.isSiteLocalAddress
                ) continue

                val ip = address.hostAddress ?: continue
                result += Candidate(name, ip, score(name, ip))
            }
        }
        return result.distinctBy { it.address }.sortedByDescending { it.score }
    }

    private fun isClearlyNotHotspot(name: String): Boolean = listOf(
        "rmnet", "pdp", "ccmni", "tun", "tap", "vpn", "dummy", "lo",
    ).any { name.startsWith(it) }

    private fun score(name: String, ip: String): Int {
        var score = when {
            name.startsWith("ap") || name.contains("softap") -> 120
            name.startsWith("swlan") -> 110
            name.startsWith("wlan") -> 80
            name.startsWith("eth") -> 40
            else -> 20
        }
        if (ip.endsWith(".1")) score += 25
        if (ip.startsWith("192.168.")) score += 15
        return score
    }
}
