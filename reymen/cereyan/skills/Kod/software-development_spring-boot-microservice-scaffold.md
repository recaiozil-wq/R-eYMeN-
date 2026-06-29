
> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Software Development_Spring Boot Microservice Scaffold |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: spring-boot-microservice-scaffold
description: >-
title: "Spring Boot Microservice Scaffold"
  (Spring Cloud Gateway + JWT), Product/Order/User servisleri (Feign client).
  5 servisli tam stack.
domain: java, spring-boot, microservice, eureka, feign, cloud-gateway
trigger: >-
  Mikroservis mimarisi kurulacaksa, Eureka + Gateway + Feign kullanılacaksa,
  Spring Cloud projesi başlatılacaksa
version: "1.0"

audience: contributor
tags: [coding, development]
category: software-development---Spring Boot mikroservis mimarisi scaffold — Eureka Server, API Gateway



# Spring Boot Mikroservis Scaffold

Spring Boot 3.4.x + Spring Cloud 2024 ile 5 servisli mikroservis mimarisi:
Eureka Server + API Gateway + Product Service + Order Service + User Service.

Hepsi aynı parent `pom.xml` altında. Ana port: **Gateway 8080**, Eureka **8761**.

## Klasör Yapısı

```
e-ticaret-mikroservis/
├── pom.xml                          (parent — Spring Cloud BOM burada)
├── test_services.sh                (başlatma sırası scripti)
├── service-registry/               (Eureka Server, port 8761)
├── api-gateway/                    (Spring Cloud Gateway, port 8080)
├── product-service/                (JPA + H2, random port)
├── order-service/                  (JPA + H2 + Feign → Product)
└── user-service/                   (JPA + H2 + JWT Auth)
```

## Başlatma Sırası (ZORUNLU)

1. **service-registry** (önce bu — port 8761)
2. **user-service, product-service, order-service** (paralel, random port)
3. **api-gateway** (en son — port 8080, Eureka'dan servisleri keşfeder)

Her servis arasında ~6-8 sn beklenmeli.

## 1. Parent pom.xml

```xml
<groupId>com.eticaret</groupId>
<artifactId>e-ticaret-mikroservis</artifactId>
<version>1.0.0</version>
<packaging>pom</packaging>

<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.4.4</version>
</parent>

<properties>
    <java.version>17</java.version>
    <spring-cloud.version>2024.0.1</spring-cloud.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<modules>
    <module>service-registry</module>
    <module>api-gateway</module>
    <module>product-service</module>
    <module>order-service</module>
    <module>user-service</module>
</modules>
```

## 2. Service Registry (Eureka Server)

**pom.xml:** `spring-cloud-starter-netflix-eureka-server`

```java
@SpringBootApplication
@EnableEurekaServer
public class ServiceRegistryApplication { ... }
```

**application.yml:** port 8761, `register-with-eureka: false`, `fetch-registry: false`

## 3. API Gateway (Spring Cloud Gateway)

**pom.xml:** `spring-cloud-starter-gateway`, `spring-cloud-starter-netflix-eureka-client`, `jjwt-api/impl/jackson`

```java
@SpringBootApplication
@EnableDiscoveryClient
public class ApiGatewayApplication { ... }
```

**route yapılandırması:**

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-service
          uri: lb://user-service
          predicates:
            - Path=/api/auth/**
        - id: product-service
          uri: lb://product-service
          predicates:
            - Path=/api/products/**,/api/categories/**
        - id: order-service
          uri: lb://order-service
          predicates:
            - Path=/api/orders/**
```

**JWT Filter (Gateway):** `/api/auth/**` bypass eder, diğer tüm yollar JWT doğrulaması yapar.
Gateway JWT filter'ı `GlobalFilter` arayüzünü implemente eder, `/api/auth/**` dışındaki tüm isteklerde `Authorization` header'ından token okur, `X-User-Email` header'ını servislere iletir.

## 4. Product Service

**pom.xml:** `web`, `data-jpa`, `validation`, `eureka-client`, `h2`, `lombok`

```java
@SpringBootApplication
@EnableDiscoveryClient
public class ProductServiceApplication { ... }
```

Entity'ler: `Product`, `Category`. Repository: `ProductRepository`, `CategoryRepository`.
Service: `ProductService` (CRUD + Category CRUD). Controller: `ProductController`.

**ÖNEMLİ:** `Category.products` alanında `@OneToMany(mappedBy = "category")` — get işlemlerinde StackOverflow'u önlemek için DTO kullan.

**port:** `server.port: 0` (random, Eureka üzerinden keşfedilir)

## 5. Order Service (Feign Client ile)

**pom.xml:** `eureka-client`, `openfeign`, ayrıca `web`, `data-jpa`, `validation`, `h2`, `lombok`

```java
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class OrderServiceApplication { ... }
```

**Feign Client:**
```java
@FeignClient(name = "product-service")
public interface ProductServiceClient {
    @GetMapping("/api/products/{id}")
    ProductDto getProduct(@PathVariable("id") Long id);
}
```

Entity'ler: `Order`, `OrderItem`. **OrderItem'da `@ManyToOne Order order` — LAZY fetch, @JsonIgnore ekle.**
Service: OrderService — sipariş oluştururken Feign ile Product Service'ten ürün bilgisi alır.
Controller: OrderController — `/api/orders` (POST create, GET list, GET by id)

**User Email:** Gateway'den `X-User-Email` header'ı ile gelir.

## 6. User Service (JWT Auth)

**pom.xml:** `web`, `data-jpa`, `validation`, `eureka-client`, `jjwt-api/impl/jackson`, `h2`, `lombok`

Entity: `User` (email, password, fullName, role, createdAt). `Role` enum: `ROLE_USER, ROLE_ADMIN`.
Repository: `UserRepository` (findByEmail, existsByEmail).
JWT Util: `JwtTokenUtil` — hmacShaKeyFor, generateToken, getEmailFromToken, validateToken.
Service: `AuthService` — register (exists check), login (password match), getUserByEmail.
Controller: `AuthController` — POST `/api/auth/register`, POST `/api/auth/login`, GET `/api/auth/me`.

**app.jwt.secret** application.yml'de tanımlanır. En az 256 bit (32 karakter).

## Önemli Kurallar (Monolitik Scaffold'dan Devralınan)

- Entity'lerde `@Data` KULLANMA → `@Getter @Setter` kullan (StackOverflow önlemi)
- Tüm `@ManyToOne` ve `@OneToMany`'de `fetch = FetchType.LAZY`
- `OrderItem`'da `@JsonIgnore private Order order` — JSON döngüsünü kır
- Feign çağrılarında `try-catch(FeignException)` — servis down olunca anlamlı hata dönsün
- Gateway'de CORS ayarlarını unutma: `spring.cloud.gateway.globalcors`

## Hata Ayıklama

| Hata | Sebep | Çözüm |
|------|-------|-------|
| Eureka'ya bağlanamıyor | Servis Registry çalışmıyor | Önce Eureka'yı başlat |
| Gateway 503 | Servis Eureka'ya kaydolmamış | Servis log'larını kontrol et |
| Feign: No available instance | Servis ismi yanlış | @FeignClient(name) ile eureka'daki spring.application.name eşleşmeli |
| Feign: 500 Internal Server Error | Hedef serviste hata | Hedef servisin log'una bak |

## Tam Çalışan Referans

`C:\Users\marko\Desktop\e-ticaret-mikroservis\` — 5 servis, 35+ Java dosyası. `mvn compile -q` ile derlenir.
