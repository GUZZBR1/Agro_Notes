<?php

declare(strict_types=1);

namespace Drupal\asset\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Render\Element;

/**
 * Theme hook implementations for asset.
 */
class ThemeHooks {

  /**
   * Implements hook_theme().
   */
  #[Hook('theme')]
  public function theme() {
    return [
      'asset' => [
        'render element' => 'elements',
        'initial preprocess' => static::class . '::preprocessAsset',
      ],
    ];
  }

  /**
   * Prepares variables for asset templates.
   *
   * Default template: asset.html.twig.
   *
   * @param array $variables
   *   An associative array containing:
   *   - elements: An associative array containing the asset information and any
   *     fields attached to the asset. Properties used:
   *     - #asset: A \Drupal\asset\Entity\Asset object. The asset entity.
   *   - attributes: HTML attributes for the containing element.
   */
  public function preprocessAsset(array &$variables) {
    $variables['asset'] = $variables['elements']['#asset'];
    // Helpful $content variable for templates.
    foreach (Element::children($variables['elements']) as $key) {
      $variables['content'][$key] = $variables['elements'][$key];
    }
  }

  /**
   * Implements hook_theme_suggestions_HOOK().
   */
  #[Hook('theme_suggestions_asset')]
  public function themeSuggestionsAsset(array $variables) {
    $suggestions = [];
    $asset = $variables['elements']['#asset'];
    $sanitized_view_mode = strtr($variables['elements']['#view_mode'], '.', '_');
    $suggestions[] = 'asset__' . $sanitized_view_mode;
    $suggestions[] = 'asset__' . $asset->bundle();
    $suggestions[] = 'asset__' . $asset->bundle() . '__' . $sanitized_view_mode;
    $suggestions[] = 'asset__' . $asset->id();
    $suggestions[] = 'asset__' . $asset->id() . '__' . $sanitized_view_mode;
    return $suggestions;
  }

}
