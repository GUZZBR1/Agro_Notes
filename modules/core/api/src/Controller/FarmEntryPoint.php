<?php

declare(strict_types=1);

namespace Drupal\farm_api\Controller;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Extension\ProfileExtensionList;
use Drupal\Core\Session\AccountInterface;
use Drupal\jsonapi\CacheableResourceResponse;
use Drupal\jsonapi\Controller\EntryPoint;
use Drupal\jsonapi\JsonApiResource\JsonApiDocumentTopLevel;
use Drupal\jsonapi\JsonApiResource\NullIncludedData;
use Drupal\jsonapi\JsonApiResource\ResourceObjectData;
use Drupal\jsonapi\ResourceType\ResourceTypeRepositoryInterface;

/**
 * Extend the core jsonapi EntryPoint controller.
 *
 * Adds a "meta.farm" key to root /api endpoint.
 *
 * @ingroup farm
 *
 * PHPStan throws the following error on the next line:
 * Class Drupal\farm_api\Controller\FarmEntryPoint extends @internal class
 * Drupal\jsonapi\Controller\EntryPoint.
 * We ignore this because we intentionally extend the core JSON:API controller,
 * even though it is marked @internal, and take responsibility for it working
 * correctly.
 * @phpstan-ignore-next-line
 */
class FarmEntryPoint extends EntryPoint {

  use AutowireTrait;

  public function __construct(
    ResourceTypeRepositoryInterface $resourceTypeRepository,
    AccountInterface $user,
    protected ProfileExtensionList $profileExtensionList,
  ) {
    parent::__construct($resourceTypeRepository, $user);
  }

  /**
   * {@inheritdoc}
   */
  public function index() {

    // Get the base url.
    global $base_url;

    // Get normal response cache and data.
    /** @var \Drupal\jsonapi\CacheableResourceResponse $response */
    $response = parent::index();
    $cacheability = $response->getCacheableMetadata();
    $data = $response->getResponseData();

    // Get urls and meta.
    $urls = $data->getLinks();
    $meta = $data->getMeta();

    // Get the farmOS profile info.
    $farm_profile_info = $this->profileExtensionList->getExtensionInfo('farm');

    // Add a "farm" object to meta.
    $meta['farm'] = [
      'name' => $this->config('system.site')->get('name'),
      'url' => $base_url,
      'version' => $farm_profile_info['version'],
    ];

    // Allow modules to add additional meta information.
    $this->moduleHandler()->alter('farm_api_meta', $meta['farm']);

    // Build a new response.
    $new_response = new CacheableResourceResponse(new JsonApiDocumentTopLevel(new ResourceObjectData([]), new NullIncludedData(), $urls, $meta));

    // Add the original response's cacheability.
    $new_response->addCacheableDependency($cacheability);

    return $new_response;
  }

}
