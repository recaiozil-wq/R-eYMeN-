
> **Kategori:** software-development

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Software Development_Spring Boot Scaffold |
| **Nerede?** | software-development/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---
name: spring-boot-scaffold
description: >-
title: "Spring Boot Scaffold"
  Repository → Service → Security → Controller sırası.  10 farklı proje tipini
  kapsayan şablon.
domain: java, spring-boot, jpa, jwt, rest-api
trigger: Spring Boot projesi oluşturulacaksa, JPA entity + JWT auth + REST
  API yazılacaksa, mevcut Spring Boot kodunda login/403/StackOverflow hatası
  varsa
version: "1.0"

audience: contributor
tags: [coding, development]
category: software-development---Spring Boot projesi (JPA + JWT + H2) baştan sona scaffold. Entity → DTO →



# Spring Boot Scaffold Skill

Spring Boot 3.4.x + JPA + H2 + JWT + Lombok + Validation ile REST API scaffold.
Her proje için **31+ dosya** — entity'den controller'a kadar eksiksiz.

## Klasör Yapısı

```
proje-adi/
├── pom.xml
├── src/main/resources/application.yml
└── src/main/java/com/proje/
    ├── ProjeApplication.java
    ├── entity/        (5+ sınıf: Product, Category, User, Order, OrderItem)
    ├── dto/           (8+ sınıf: Request/Response çiftleri)
    ├── repository/    (4+ interface)
    ├── service/       (4+ sınıf + ResourceNotFoundException)
    ├── security/      (3 sınıf: JwtTokenProvider, JwtAuthFilter, SecurityConfig)
    └── controller/    (4+ sınıf)
```

## Adım Adım

### 1. Maven + Spring Boot Kurulumu

```bash
# Windows portable Maven
export JAVA_HOME="/c/Program Files/Eclipse Adoptium/jdk-17.0.19.10-hotspot"
export PATH="$JAVA_HOME/bin:/c/Users/marko/Desktop/proje-adi/apache-maven-3.9.9/bin:$PATH"
```

### 2. pom.xml Yazarken Dikkat Edilecekler

- Spring Boot Parent: `3.4.4`
- `spring-boot-starter-web`, `data-jpa`, `security`, `validation`
- Lombok: **annotationProcessorPaths** bloğu EKLENMELİ — yoksa `mvn compile` Lombok annotation'larını işlemez
- H2: runtime scope (in-memory test için)
- jjwt-api/impl/jackson: 0.12.6

```xml
<annotationProcessorPaths>
    <path>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
    </path>
</annotationProcessorPaths>
```

### 3. Entity Yazımı — KRİTİK KURALLAR

#### `@Data` KULLANMA — `@Getter @Setter` KULLAN

Hibernate entity'lerde **`@Data` yerine `@Getter @Setter`** kullan. Sebebi:
- `@Data` = `@Getter + @Setter + @RequiredArgsConstructor + @ToString + @EqualsAndHashCode`
| `@EqualsAndHashCode` lazy proxy'leri çağırır, StackOverflow'a yol açar — **özellikle Set<OrderItem> gibi koleksiyon alanları ile**
- `@ToString` tüm ilişkileri eager fetch eder, performansı öldürür
- **AYRICA:** `@Data` Lombok'un `equals()` ve `hashCode()`'u tüm alanları kullanır. Hibernate proxy nesneleri (LAZY yüklenen ilişkiler) bu metodları çağırdığında session kapalıysa LazyInitializationException, açıksa StackOverflow verir.
- **Kesin kural:** Entity'lerde `@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor` — `@Data` ASLA kullanma

```java
@Entity
@Getter @Setter          // DOGRU
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product { ... }

// @Data                   // YANLIS — hibernate ile sorun cikarir
```

#### JSON Döngü Kırma

`OrderItem.order → Order` ilişkisinde:

```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "order_id", nullable = false)
@JsonIgnore                   // OrderItem icinde order'i JSON'a dahil etme
private Order order;
```

#### LAZY Fetching

Tüm `@ManyToOne` ve `@OneToMany` ilişkilerinde `fetch = FetchType.LAZY` kullan.

### 4. SecurityConfig — SIK YAPILAN HATALAR

#### UserDetailsService Bean'i EKLE

```java
@Bean
public UserDetailsService userDetailsService() {
    return email -> userRepository.findByEmail(email)
            .map(user -> org.springframework.security.core.userdetails.User.builder()
                    .username(user.getEmail())
                    .password(user.getPassword())
                    .roles(user.getRole().name().replace("ROLE_", ""))
                    .build())
            .orElseThrow(() -> new UsernameNotFoundException("Kullanici bulunamadi: " + email));
}
```

Bu bean **olmazsa** login hep 403 döner — AuthenticationManager kullanıcıyı bulamaz.

#### Public GET Endpoint'leri

```java
.requestMatchers("/api/auth/**").permitAll()
.requestMatchers("/api/admin/**").hasRole("ADMIN")
.requestMatchers(HttpMethod.GET, "/api/products/**", "/api/categories/**").permitAll()
.anyRequest().authenticated()
```

### 5. GlobalExceptionHandler — HER ZAMAN EKLE

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<?> handleNotFound(ResourceNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(errorBody(404, ex.getMessage()));
    }
    // IllegalArgumentException -> 400, BadCredentialsException -> 401, Exception -> 500
}
```

Bu olmazsa servis hatalari (ResourceNotFound, IllegalArgumentException) Spring'e **403 (Access Denied)** olarak yansir.

### 6. Service -> DTO Donusumu

Entity'leri direkt JSON'a serializelama. Controller her zaman DTO dondursun:

```java
public OrderResponse toResponse(Order order) {
    OrderResponse resp = new OrderResponse();
    resp.setId(order.getId());
    resp.setItems(order.getOrderItems().stream().map(item -> {
        OrderItemResponse ir = new OrderItemResponse();
        ir.setProductName(item.getProduct().getName());
        return ir;
    }).collect(Collectors.toSet()));
    return resp;
}
```

## Sik Karsilasilan Hatalar ve Cozumleri

| Hata | Sebep | Cozum |
|------|-------|-------|
| Login 403 | UserDetailsService bean'i yok | userDetailsService() bean'ini ekle |
| Register sonrasi 403 | Kullanici zaten kayitli | DB'yi temizle veya existsByEmail kontrolu |
| StackOverflowError (Order) | @Data + JSON dongu | @Data -> @Getter @Setter, @JsonIgnore ekle |
| Maven compile Lombok hatasi | annotationProcessorPaths eksik | pom.xml'e annotationProcessorPaths blogu ekle |
| Servlet.service() 403 | GlobalExceptionHandler yok | @RestControllerAdvice ekle |

## Test Akisi

1. Register -> POST /api/auth/login -> token al
2. Header: `Authorization: Bearer <token>`
3. Public GET endpoints token'siz calismali
4. Private POST/PUT/DELETE token'siz 403 donmeli
5. Siparis olusturma (Order) StackOverflow vermemeli

## Proje Referanslari

references/ klasorunde her proje icin ayri dosya tut:
- references/proje-1-eticaret-backend.md
- references/proje-2-mikroservis.md
- ... (proje basina bir referans dosyasi)

## Kaynak Kod

Tam calisan ornek: C:\\Users\\marko\\Desktop\\e-ticaret-backend\\ (31 dosya, port 8080)

## İlgili Skill'ler

- **spring-boot-microservice-scaffold** — 5 servisli Eureka+Gateway+Feign mimarisi (servis-registry, api-gateway, product/order/user servisleri). Aynı Spring Boot + JPA + JWT stack'ini mikroservis deseniyle kurar.
- Bu skill tek monolitik projeler için, mikroservis skill'i distributed mimariler için kullanılır.
