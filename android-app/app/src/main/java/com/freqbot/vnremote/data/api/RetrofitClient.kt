package com.freqbot.vnremote.data.api

import android.content.Context
import android.util.Base64
import com.freqbot.vnremote.data.model.ServerConfig
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Quản lý kết nối HTTP tới máy chủ Freqtrade, lưu cấu hình IP VPS / Tailscale
 * và tự động đính kèm Bearer JWT Token vào Header.
 */
object RetrofitClient {

    private const val PREF_NAME = "freqbot_vn_prefs"
    private const val KEY_SERVER_URL = "server_url"
    private const val KEY_USERNAME = "username"
    private const val KEY_PASSWORD = "password"

    // Mặc định 10.0.2.2:8080 để chạy ngay trên Android Emulator nối vào máy tính chạy Mock/Docker
    // Khi chạy thực tế qua Tailscale VPN, đổi thành http://100.x.y.z:8080/
    private const val DEFAULT_URL = "http://10.0.2.2:8080/"
    private const val DEFAULT_USER = "admin"
    private const val DEFAULT_PASS = "mat_khau_manh_cua_ban"

    @Volatile
    var jwtToken: String? = null

    fun taoChuoiBasicAuth(user: String, pass: String): String {
        val credentials = "$user:$pass"
        return "Basic " + Base64.encodeToString(credentials.toByteArray(Charsets.UTF_8), Base64.NO_WRAP)
    }

    fun chuanHoaUrl(rawUrl: String): String {
        var url = rawUrl.trim()
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://$url"
        }
        if (!url.endsWith("/")) {
            url += "/"
        }
        return url
    }

    fun luuCauHinh(context: Context, url: String, user: String, pass: String) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(KEY_SERVER_URL, chuanHoaUrl(url))
            .putString(KEY_USERNAME, user.trim())
            .putString(KEY_PASSWORD, pass)
            .apply()
    }

    fun docCauHinh(context: Context): ServerConfig {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        val url = prefs.getString(KEY_SERVER_URL, DEFAULT_URL) ?: DEFAULT_URL
        val user = prefs.getString(KEY_USERNAME, DEFAULT_USER) ?: DEFAULT_USER
        val pass = prefs.getString(KEY_PASSWORD, DEFAULT_PASS) ?: DEFAULT_PASS
        return ServerConfig(chuanHoaUrl(url), user, pass)
    }

    fun getApi(serverUrl: String = DEFAULT_URL): FreqtradeApi {
        val client = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val reqBuilder = chain.request().newBuilder()
                // Nếu đã có JWT Token và request chưa có Authorization thì tự động gắn Bearer Token
                jwtToken?.let { token ->
                    if (chain.request().header("Authorization") == null) {
                        reqBuilder.addHeader("Authorization", "Bearer $token")
                    }
                }
                chain.proceed(reqBuilder.build())
            }
            .build()

        return Retrofit.Builder()
            .baseUrl(chuanHoaUrl(serverUrl))
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(FreqtradeApi::class.java)
    }
}
